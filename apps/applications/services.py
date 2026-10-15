"""
Servicios de `applications`.

- CR-05 + CR-07: `crear_postulacion` calcula el Match Score con el motor de
  matching y lo congela (snapshot) en `match_factores` en el instante exacto
  en que el usuario aplica. Nunca se recalcula después (CR-12: cambios de
  perfil posteriores no alteran postulaciones ya registradas).
- CR-08 + CR-09: `aceptar_postulacion` es la aceptación transaccional y el
  bloqueo por carga/disponibilidad.

Orden de locks (anti-deadlock, respetarlo también en el futuro flujo de
invitaciones): postulación → vacante → perfil.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Perfil, UsuarioHabilidad, UsuarioTecnologia
from apps.matching.engine import PerfilMatching, VacanteMatching, calcular_match_score
from apps.matching.models import ConfiguracionPesosMatching
from apps.projects.models import (
    Proyecto,
    Vacante,
    VacanteHabilidadRequerida,
    VacanteTecnologiaRequerida,
)

from .models import Postulacion

ESTADOS_ACEPTABLES = {Postulacion.ESTADO_PENDIENTE, Postulacion.ESTADO_PRESELECCIONADA}

INDICE_POSTULACION_ACTIVA = "ux_postulacion_activa_unica"

# No está definida en ninguna fuente del esquema (DEVMATCH-BD §7: el
# cálculo de sobrecarga es responsabilidad de Django, no de la base).
# Constante fija por ahora, igual al default de disponibilidad_horas_semana;
# horas_de_membresia() es el único punto que habría que tocar si algún día
# se agrega Vacante.horas_semana_estimadas.
HORAS_POR_MEMBRESIA_ACTIVA = 10


class PostulacionDuplicadaError(Exception):
    """Ya existe una postulación pendiente/preseleccionada a esta vacante
    (ux_postulacion_activa_unica). Volver a postularse tras un rechazo o
    retiro SÍ está permitido -- solo se bloquea mientras hay una activa."""


class ConfiguracionPesosNoDisponibleError(Exception):
    """No hay una fila activa en configuracion_pesos_matching, así que no
    se puede calcular (ni explicar) el Match Score."""


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


def _construir_perfil_matching(usuario):
    # El Perfil NO se crea automáticamente al registrarse: las vistas de
    # accounts lo crean con get_or_create la primera vez que el usuario
    # entra a editarlo. Aquí se hace igual, para que un usuario que aún
    # no completó su perfil pueda postularse con los valores por defecto
    # (principiante, 0 años, 10 hrs/semana) en vez de romper.
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    habilidades_ids = set(
        UsuarioHabilidad.objects.filter(usuario=usuario).values_list(
            "habilidad_id", flat=True
        )
    )
    tecnologias_ids = set(
        UsuarioTecnologia.objects.filter(usuario=usuario).values_list(
            "tecnologia_id", flat=True
        )
    )
    return PerfilMatching(
        habilidades_ids=habilidades_ids,
        tecnologias_ids=tecnologias_ids,
        nivel=perfil.nivel,
        experiencia_anios=perfil.experiencia_anios,
        disponibilidad_horas_semana=perfil.disponibilidad_horas_semana,
    )


def _construir_vacante_matching(vacante):
    habilidades_ids = set(
        VacanteHabilidadRequerida.objects.filter(vacante=vacante).values_list(
            "habilidad_id", flat=True
        )
    )
    tecnologias_ids = set(
        VacanteTecnologiaRequerida.objects.filter(vacante=vacante).values_list(
            "tecnologia_id", flat=True
        )
    )
    return VacanteMatching(
        habilidades_requeridas_ids=habilidades_ids,
        tecnologias_requeridas_ids=tecnologias_ids,
    )


def crear_postulacion(usuario, vacante):
    """
    Devuelve la Postulacion creada.

    NO valida que la vacante esté abierta ni que el proyecto sea visible
    (no esté en borrador): esa regla corresponde a las vistas, según
    DEVMATCH-BD.md §7 y §9. Ver docs/DEVMATCH-MATCHING.md, sección 6.

    Levanta:
    - PostulacionDuplicadaError si el usuario ya tiene una postulación
      activa a esta vacante -- capturarla en la vista y mostrar el mensaje
      amigable correspondiente.
    - ConfiguracionPesosNoDisponibleError si no hay pesos activos en la BD.
    """
    try:
        pesos_activos = ConfiguracionPesosMatching.objects.get(es_activo=True)
    except ConfiguracionPesosMatching.DoesNotExist as exc:
        raise ConfiguracionPesosNoDisponibleError(
            "No hay una configuración de pesos activa en "
            "configuracion_pesos_matching; no se puede calcular el Match Score."
        ) from exc

    pesos = {
        "habilidades": float(pesos_activos.peso_habilidades),
        "nivel": float(pesos_activos.peso_nivel),
        "tecnologias": float(pesos_activos.peso_tecnologias),
        "experiencia": float(pesos_activos.peso_experiencia),
        "disponibilidad": float(pesos_activos.peso_disponibilidad),
    }

    perfil_matching = _construir_perfil_matching(usuario)
    vacante_matching = _construir_vacante_matching(vacante)
    score, factores = calcular_match_score(perfil_matching, vacante_matching, pesos)

    try:
        with transaction.atomic():
            return Postulacion.objects.create(
                vacante=vacante,
                postulante=usuario,
                match_score=Decimal(str(score)),
                match_factores=factores,
                pesos_usados=pesos_activos,
            )
    except IntegrityError as exc:
        # Solo se traduce el error del índice único parcial; cualquier otra
        # violación de integridad se deja pasar tal cual para no
        # disfrazarla de "postulación duplicada".
        if INDICE_POSTULACION_ACTIVA in str(exc):
            raise PostulacionDuplicadaError(
                "Ya tienes una postulación activa a esta vacante."
            ) from exc
        raise


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
    perfil, _ = Perfil.objects.select_for_update().get_or_create(usuario=usuario)
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
        # select_for_update(), en este orden (postulación → vacante →
        # perfil, ver verificar_carga), para que una segunda aceptación
        # concurrente de la MISMA vacante espere aquí en vez de leer un
        # conteo de cupos ya desactualizado: al despertar relee el estado
        # ya committeado por la primera y sale con un VacanteSinCupo
        # limpio, no con el IntegrityError crudo de chk_cupos_no_exceden.
        postulacion = Postulacion.objects.select_for_update().get(pk=postulacion.pk)

        if postulacion.estado not in ESTADOS_ACEPTABLES:
            raise PostulacionNoAceptable(
                f"La postulación está en estado '{postulacion.estado}', no se puede aceptar."
            )

        vacante = Vacante.objects.select_for_update().get(pk=postulacion.vacante_id)
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

        membresia = EquipoMembresia.objects.create(
            proyecto=vacante.proyecto,
            vacante=vacante,
            usuario=postulacion.postulante,
            postulacion=postulacion,
        )
        # TODO(CR-14, Etapa 3): audit/services.py: log_action("postulacion.aceptada", ...)
        return membresia
