"""Utilidades compartidas por los tests que necesitan llevar un proyecto a un
estado concreto.

Desde que `trg_validar_transicion_proyecto` está activo en la base de datos de
pruebas (apps/core/migrations/0001_triggers_postgres.py), un proyecto solo
alcanza un estado recorriendo la cadena válida. Antes, cuando los triggers solo
existían en docs/devmatch_schema_v1.sql y no en la BD de test, los tests podían
saltarse directamente a cualquier estado en su setUp; eso ya no es posible.

Reutiliza `services.TRANSICIONES_VALIDAS` en vez de duplicar la tabla, para que
el helper no pueda divergir del trigger ni del servicio.
"""

from collections import deque

from apps.projects import services


def camino_valido(desde, hasta):
    """Camino más corto de estados entre `desde` y `hasta`.

    Devuelve una lista de estados intermedios, [] si ya está en `hasta`, o
    None si no existe camino (un estado terminal no tiene salida).
    """
    if desde == hasta:
        return []
    vistos = {desde}
    cola = deque([(desde, [])])
    while cola:
        actual, pasos = cola.popleft()
        for siguiente in sorted(services.TRANSICIONES_VALIDAS.get(actual, set())):
            if siguiente in vistos:
                continue
            nuevos_pasos = pasos + [siguiente]
            if siguiente == hasta:
                return nuevos_pasos
            vistos.add(siguiente)
            cola.append((siguiente, nuevos_pasos))
    return None


def lleva_a(proyecto, estado_destino):
    """Lleva `proyecto` a `estado_destino` recorriendo transiciones válidas.

    Cada paso se persiste con un save() normal, de modo que el trigger valida
    cada transición. `finalizado_en` / `cancelado_en` los escribe el propio
    trigger, no este helper.
    """
    pasos = camino_valido(proyecto.estado, estado_destino)
    if pasos is None:
        raise AssertionError(
            f"No hay camino válido de '{proyecto.estado}' a '{estado_destino}'."
        )
    for paso in pasos:
        proyecto.estado = paso
        proyecto.save()
    proyecto.refresh_from_db()
    return proyecto