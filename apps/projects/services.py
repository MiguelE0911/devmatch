"""
Capa inicial de servicios de `projects` (Etapa 1).

Replica en Python la misma máquina de estados que ya aplica el trigger
`fn_validar_transicion_proyecto` en la base real (ver DevMatch-BD, 6.3),
para poder mostrar un mensaje de error amigable en la interfaz en vez de
depender del IntegrityError/OperationalError crudo de Postgres. El
trigger sigue siendo la garantía final: si algo se escapa aquí, la base
de datos igual rechaza la transición.

La versión completa (integrada con auditoría y permisos por rol) se
termina en Etapa 3 (CR-02, CR-14) — ver DEVMATCH-DISTRIBUCION.md.

Vacantes (Etapa 2): `crear_vacante` y `actualizar_vacante` concentran las
reglas de negocio del alta/edición de una vacante y la sincronización de
sus requisitos (tablas puente), todo dentro de `transaction.atomic()`.
`VacanteForm` solo valida y delega aquí.
"""

from django.db import transaction
from django.utils import timezone

from .models import (
    Proyecto,
    Vacante,
    VacanteHabilidadRequerida,
    VacanteTecnologiaRequerida,
)


class TransicionEstadoInvalida(Exception):
    """Se intentó pasar un proyecto de un estado a otro no permitido."""


TRANSICIONES_VALIDAS = {
    Proyecto.ESTADO_BORRADOR: {Proyecto.ESTADO_PUBLICADO, Proyecto.ESTADO_CANCELADO},
    Proyecto.ESTADO_PUBLICADO: {Proyecto.ESTADO_RECLUTANDO, Proyecto.ESTADO_CANCELADO},
    Proyecto.ESTADO_RECLUTANDO: {
        Proyecto.ESTADO_EQUIPO_COMPLETO,
        Proyecto.ESTADO_CANCELADO,
    },
    Proyecto.ESTADO_EQUIPO_COMPLETO: {
        Proyecto.ESTADO_EN_DESARROLLO,
        Proyecto.ESTADO_RECLUTANDO,
        Proyecto.ESTADO_CANCELADO,
    },
    Proyecto.ESTADO_EN_DESARROLLO: {
        Proyecto.ESTADO_FINALIZADO,
        Proyecto.ESTADO_CANCELADO,
    },
    Proyecto.ESTADO_FINALIZADO: set(),
    Proyecto.ESTADO_CANCELADO: set(),
}


def cambiar_estado(proyecto: Proyecto, nuevo_estado: str) -> Proyecto:
    """
    Cambia el estado de `proyecto` validando la transición contra
    TRANSICIONES_VALIDAS. Si el nuevo estado es igual al actual, no hace
    nada (mismo comportamiento que el trigger). Al finalizar o cancelar,
    registra finalizado_en/cancelado_en automáticamente.
    """
    estado_actual = proyecto.estado
    if nuevo_estado == estado_actual:
        return proyecto

    permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
    if nuevo_estado not in permitidos:
        raise TransicionEstadoInvalida(
            f"No se puede pasar el proyecto de '{estado_actual}' a '{nuevo_estado}'."
        )

    proyecto.estado = nuevo_estado
    if nuevo_estado == Proyecto.ESTADO_FINALIZADO:
        proyecto.finalizado_en = timezone.now()
    elif nuevo_estado == Proyecto.ESTADO_CANCELADO:
        proyecto.cancelado_en = timezone.now()
    proyecto.save()
    return proyecto


# ---------------------------------------------------------------------------
# VACANTES
# ---------------------------------------------------------------------------


class VacanteInvalida(Exception):
    """Base de los errores de negocio al crear o editar una vacante. Las
    vistas capturan esta clase y muestran `str(exc)` al usuario."""


class ProyectoNoAceptaVacantes(VacanteInvalida):
    """El proyecto está finalizado o cancelado: no admite vacantes nuevas
    ni reabrir las canceladas (spec: un proyecto Finalizado no podrá abrir
    nuevas vacantes)."""


class TransicionVacanteInvalida(VacanteInvalida):
    """Cambio manual de estado de la vacante no permitido."""


ESTADOS_PROYECTO_SIN_VACANTES = frozenset(
    {Proyecto.ESTADO_FINALIZADO, Proyecto.ESTADO_CANCELADO}
)

# Transiciones que el usuario puede pedir a mano. 'cubierta' NO es un estado
# de entrada manual: lo asigna el trigger fn_actualizar_cupos_vacante cuando
# los cupos se llenan (ver DevMatch-BD 6.2), y desde 'cubierta' no se puede
# cambiar el estado a mano (la vacante vuelve a 'abierta' sola al liberarse
# un cupo).
TRANSICIONES_VACANTE_MANUALES = {
    Vacante.ESTADO_ABIERTA: {Vacante.ESTADO_CANCELADA},
    Vacante.ESTADO_CANCELADA: {Vacante.ESTADO_ABIERTA},  # reapertura explícita
    Vacante.ESTADO_CUBIERTA: set(),
}


def _sincronizar_habilidades(vacante, habilidades):
    habilidades = list(habilidades)
    ids = {h.pk for h in habilidades}
    for puente in vacante.vacantehabilidadrequerida_set.all():
        if puente.habilidad_id not in ids:
            puente.delete()
    for habilidad in habilidades:
        VacanteHabilidadRequerida.objects.get_or_create(
            vacante=vacante, habilidad=habilidad
        )


def _sincronizar_tecnologias(vacante, tecnologias):
    tecnologias = list(tecnologias)
    ids = {t.pk for t in tecnologias}
    for puente in vacante.vacantetecnologiarequerida_set.all():
        if puente.tecnologia_id not in ids:
            puente.delete()
    for tecnologia in tecnologias:
        VacanteTecnologiaRequerida.objects.get_or_create(
            vacante=vacante, tecnologia=tecnologia
        )


def sincronizar_requisitos(vacante, habilidades=(), tecnologias=()):
    """Deja los requisitos de la vacante exactamente como se indican: borra
    las filas puente que sobran y crea las que faltan. Atómico."""
    with transaction.atomic():
        _sincronizar_habilidades(vacante, habilidades)
        _sincronizar_tecnologias(vacante, tecnologias)


def _estado_resultante(vacante, estado_solicitado, cupos_totales):
    """Decide el estado final de la vacante al editarla, o levanta un error.

    `vacante` es el registro tal como está en la base (con `proyecto`
    cargado); `cupos_totales` es el valor que se quiere guardar.
    """
    actual = vacante.estado
    nuevo = actual

    if estado_solicitado and estado_solicitado != actual:
        if estado_solicitado == Vacante.ESTADO_CUBIERTA:
            raise TransicionVacanteInvalida(
                "El estado 'cubierta' lo asigna el sistema cuando se llenan "
                "los cupos; no se puede elegir manualmente."
            )
        if estado_solicitado not in TRANSICIONES_VACANTE_MANUALES.get(actual, set()):
            raise TransicionVacanteInvalida(
                f"No se puede pasar la vacante de '{actual}' a "
                f"'{estado_solicitado}'."
            )
        if estado_solicitado == Vacante.ESTADO_ABIERTA:  # reapertura
            if vacante.proyecto.estado in ESTADOS_PROYECTO_SIN_VACANTES:
                raise ProyectoNoAceptaVacantes(
                    "No se puede reabrir la vacante: el proyecto está "
                    f"{vacante.proyecto.estado}."
                )
            if vacante.cupos_ocupados >= cupos_totales:
                raise TransicionVacanteInvalida(
                    "No se puede reabrir la vacante: no tiene cupos libres."
                )
        nuevo = estado_solicitado

    # Una vacante cancelada se queda cancelada. En cualquier otro caso el
    # estado sigue a los cupos: el trigger solo corre al cambiar membresías,
    # así que si se edita `cupos_totales` hay que reflejarlo aquí con la misma
    # regla del trigger (cubierta si ocupados >= totales, abierta si no).
    if nuevo != Vacante.ESTADO_CANCELADA:
        nuevo = (
            Vacante.ESTADO_CUBIERTA
            if vacante.cupos_ocupados >= cupos_totales
            else Vacante.ESTADO_ABIERTA
        )
    return nuevo


def crear_vacante(
    proyecto, *, titulo, descripcion, cupos_totales, habilidades=(), tecnologias=()
):
    """Crea una vacante abierta con sus requisitos. Todo o nada.

    Rechaza el alta si el proyecto está finalizado o cancelado. El estado del
    proyecto se relee con bloqueo de fila, para que no cambie entre la
    validación y el INSERT.
    """
    with transaction.atomic():
        proyecto = Proyecto.objects.select_for_update().get(pk=proyecto.pk)
        if proyecto.estado in ESTADOS_PROYECTO_SIN_VACANTES:
            raise ProyectoNoAceptaVacantes(
                "No se pueden agregar vacantes: el proyecto está "
                f"{proyecto.estado}."
            )
        vacante = Vacante.objects.create(
            proyecto=proyecto,
            titulo=titulo,
            descripcion=descripcion,
            cupos_totales=cupos_totales,
            estado=Vacante.ESTADO_ABIERTA,
            es_activo=True,
        )
        sincronizar_requisitos(vacante, habilidades, tecnologias)
    return vacante


def actualizar_vacante(
    vacante,
    *,
    titulo,
    descripcion,
    cupos_totales,
    habilidades=(),
    tecnologias=(),
    estado=None,
):
    """Edita una vacante y sus requisitos. Todo o nada.

    `estado` es el estado que el usuario pidió (None o igual al actual = sin
    cambio manual). Solo se permite abierta -> cancelada y la reapertura
    cancelada -> abierta; 'cubierta' nunca se asigna a mano.
    """
    with transaction.atomic():
        vacante = (
            Vacante.objects.select_for_update(of=("self",))
            .select_related("proyecto")
            .get(pk=vacante.pk)
        )
        if cupos_totales < vacante.cupos_ocupados:
            raise VacanteInvalida(
                "No se puede bajar a menos de los cupos ya ocupados "
                f"({vacante.cupos_ocupados})."
            )
        nuevo_estado = _estado_resultante(vacante, estado, cupos_totales)

        vacante.titulo = titulo
        vacante.descripcion = descripcion
        vacante.cupos_totales = cupos_totales
        vacante.estado = nuevo_estado
        vacante.save(
            update_fields=[
                "titulo",
                "descripcion",
                "cupos_totales",
                "estado",
                "actualizado_en",
            ]
        )
        sincronizar_requisitos(vacante, habilidades, tecnologias)
    return vacante