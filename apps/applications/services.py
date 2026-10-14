"""
Servicios de `applications` — aceptación transaccional (CR-08) y bloqueo
por carga/disponibilidad (CR-09).

Orden de locks (anti-deadlock, respetarlo también en el futuro flujo de
invitaciones): postulación → vacante → perfil.
"""

from django.db import transaction
from django.utils import timezone

from apps.projects.models import Proyecto, Vacante

from .models import Postulacion

ESTADOS_ACEPTABLES = {Postulacion.ESTADO_PENDIENTE, Postulacion.ESTADO_PRESELECCIONADA}

# No está definida en ninguna fuente del esquema (DEVMATCH-BD §7: el
# cálculo de sobrecarga es responsabilidad de Django, no de la base).
# Constante fija por ahora, igual al default de disponibilidad_horas_semana;
# horas_de_membresia() es el único punto que habría que tocar si algún día
# se agrega Vacante.horas_semana_estimadas.
HORAS_POR_MEMBRESIA_ACTIVA = 10


class PostulacionNoAceptable(Exception):
    """La postulación no está en un estado aceptable, o el postulante ya
    es miembro activo del proyecto."""


class VacanteSinCupo(Exception):
    """La vacante no tiene cupo disponible (llena, cancelada o inactiva)."""


class CargaIncompatible(Exception):
    """La carga actual del postulante más la nueva membresía excede su
    disponibilidad declarada."""

    def __init__(self, disponibilidad, carga_actual, horas_nuevas):
        self.disponibilidad = disponibilidad
        self.carga_actual = carga_actual
        self.horas_nuevas = horas_nuevas
        super().__init__(
            f"Disponibilidad insuficiente: {carga_actual}h comprometidas + "
            f"{horas_nuevas}h nuevas > {disponibilidad}h disponibles."
        )


def horas_de_membresia(vacante) -> int:
    """Hoy es una constante; mañana puede leer Vacante.horas_semana_estimadas."""
    return HORAS_POR_MEMBRESIA_ACTIVA


def calcular_carga(usuario) -> int:
    """Horas comprometidas por membresías activas en proyectos que no han
    terminado. Un proyecto finalizado/cancelado no libera la membresía
    (ningún trigger la retira), así que hay que excluirlo explícitamente
    o la carga quedaría inflada para siempre."""
    from apps.teams.models import EquipoMembresia

    membresias = EquipoMembresia.objects.filter(
        usuario=usuario, estado=EquipoMembresia.ESTADO_ACTIVO
    ).exclude(
        proyecto__estado__in=[Proyecto.ESTADO_FINALIZADO, Proyecto.ESTADO_CANCELADO]
    )
    return membresias.count() * HORAS_POR_MEMBRESIA_ACTIVA


def verificar_carga(usuario, horas_nuevas: int) -> int:
    """Lanza CargaIncompatible si aceptar sumaría más carga de la que el
    usuario declaró poder sostener. Devuelve la carga actual (sin las
    horas nuevas) si pasa."""
    from apps.accounts.models import Perfil

    perfil = Perfil.objects.select_for_update().get(usuario=usuario)
    carga_actual = calcular_carga(usuario)
    if carga_actual + horas_nuevas > perfil.disponibilidad_horas_semana:
        raise CargaIncompatible(
            perfil.disponibilidad_horas_semana, carga_actual, horas_nuevas
        )
    return carga_actual


def aceptar_postulacion(postulacion: Postulacion, decidido_por, motivo: str = ""):
    """
    Acepta `postulacion`: marca su estado como aceptada y crea la
    membresía del equipo, todo en una sola transacción. La vacante solo
    tiene cupo real si el INSERT en equipos_membresias no viola
    chk_cupos_no_exceden — eso lo decide la base de datos (trigger
    trg_membresia_actualiza_cupos), no este código; los chequeos de aquí
    son para fallar limpio con un mensaje de negocio antes de escribir
    nada, no son la garantía real.
    """
    from apps.teams.models import EquipoMembresia

    with transaction.atomic():
        if postulacion.estado not in ESTADOS_ACEPTABLES:
            raise PostulacionNoAceptable(
                f"La postulación está en estado '{postulacion.estado}', no se puede aceptar."
            )

        vacante = postulacion.vacante
        if not vacante.es_activo or vacante.estado != Vacante.ESTADO_ABIERTA:
            raise VacanteSinCupo(
                f"La vacante no está disponible (estado='{vacante.estado}', "
                f"es_activo={vacante.es_activo})."
            )
        if vacante.cupos_ocupados >= vacante.cupos_totales:
            raise VacanteSinCupo("La vacante ya no tiene cupos disponibles.")

        # El índice único de la base (ux_membresia_activa_unica) es por
        # vacante, no por proyecto — un mismo usuario podría colarse por
        # dos vacantes distintas del mismo proyecto si no se valida aquí.
        ya_miembro_del_proyecto = EquipoMembresia.objects.filter(
            proyecto_id=vacante.proyecto_id,
            usuario=postulacion.postulante,
            estado=EquipoMembresia.ESTADO_ACTIVO,
        ).exists()
        if ya_miembro_del_proyecto:
            raise PostulacionNoAceptable(
                "El postulante ya es miembro activo de este proyecto."
            )

        horas_nuevas = horas_de_membresia(vacante)
        verificar_carga(postulacion.postulante, horas_nuevas)

        postulacion.estado = Postulacion.ESTADO_ACEPTADA
        postulacion.decidido_por = decidido_por
        postulacion.decidido_en = timezone.now()
        postulacion.motivo_decision = motivo
        postulacion.save()

        return EquipoMembresia.objects.create(
            proyecto=vacante.proyecto,
            vacante=vacante,
            usuario=postulacion.postulante,
            postulacion=postulacion,
        )
