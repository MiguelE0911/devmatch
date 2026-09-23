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
"""

from django.utils import timezone

from .models import Proyecto


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
