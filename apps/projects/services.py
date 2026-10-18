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

from .models import Proyecto, Vacante


class TransicionEstadoInvalida(Exception):
    """Se intentó pasar un proyecto de un estado a otro no permitido."""


# Un proyecto en un estado "cerrado" ya no recluta: sus vacantes abiertas no
# deben seguir recibiendo postulaciones (regla de negocio, no hay trigger que
# la aplique — ver `cerrar_vacantes_abiertas`).
ESTADOS_CERRADOS = {Proyecto.ESTADO_FINALIZADO, Proyecto.ESTADO_CANCELADO}


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


def puede_agregar_vacantes(proyecto: Proyecto) -> bool:
    """¿Se pueden agregar vacantes nuevas a `proyecto` según su estado?

    Permitidos: 'borrador', 'publicado', 'reclutando', 'equipo_completo' y
    'en_desarrollo'. Bloqueados: 'finalizado' y 'cancelado' — un proyecto
    cerrado ya no recluta, así que no debe admitir vacantes nuevas. Coincide
    con la regla de postulaciones (mismos ESTADOS_CERRADOS).
    """
    return proyecto.estado not in ESTADOS_CERRADOS


def puede_agregar_imagenes(proyecto):
    """Permite agregar imágenes solo si el proyecto NO está cancelado.

    Regla: un proyecto finalizado puede seguir subiendo imágenes de prototipos;
    un proyecto cancelado NO puede agregar nuevas imágenes.
    """
    return proyecto.estado != Proyecto.ESTADO_CANCELADO


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
    if nuevo_estado in ESTADOS_CERRADOS:
        cerrar_vacantes_abiertas(proyecto)
    return proyecto


def cerrar_vacantes_abiertas(proyecto: Proyecto) -> int:
    """Marca 'cancelada' las vacantes abiertas de un proyecto ya cerrado.

    Sin esto, un proyecto finalizado seguiría mostrando vacantes postulables
    (el único estado que el trigger `fn_actualizar_cupos_vacante` revierte es
    'abierta'/'cubierta'; 'cancelada' es terminal, así que se queda cerrada).
    No toca 'cubierta' (ya no recibe postulaciones). Devuelve cuántas cerró.
    """
    return proyecto.vacantes.filter(estado=Vacante.ESTADO_ABIERTA).update(
        estado=Vacante.ESTADO_CANCELADA
    )
