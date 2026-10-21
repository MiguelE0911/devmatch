from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.applications.models import Postulacion
from apps.applications.services import (
    ConfiguracionPesosNoDisponibleError,
    PostulacionDuplicadaError,
    VacanteNoPostulable,
    crear_postulacion,
)
from apps.projects.models import Proyecto, Vacante
from apps.projects.services import ESTADO_BADGE, ESTADOS_PROYECTO_NO_PUBLICABLE

ESTADOS_RETIRABLES = (Postulacion.ESTADO_PENDIENTE, Postulacion.ESTADO_PRESELECCIONADA)

# Una postulación "abierta" (pendiente/preseleccionada) es la única que
# bloquea al postulante: mientras lo sea, el índice único parcial
# `ux_postulacion_activa_unica` no le deja volver a postularse a la misma
# vacante.
ESTADOS_POSTULACION_ABIERTA = ESTADOS_RETIRABLES

# Estados que se pueden pedir con ?estado=. Se derivan de las choices del
# modelo para que no se queden desincronizados si se agrega uno nuevo.
ESTADOS_FILTRABLES = {valor for valor, _etiqueta in Postulacion.ESTADO_CHOICES}


def _motivo_proyecto_no_publicable(proyecto):
    """Texto que explica por qué el proyecto ya no admite postulaciones."""
    if proyecto.estado == Proyecto.ESTADO_CANCELADO:
        return f"El proyecto «{proyecto.nombre}» fue cancelado y ya no admite postulaciones."
    if proyecto.estado == Proyecto.ESTADO_FINALIZADO:
        return f"El proyecto «{proyecto.nombre}» fue finalizado y ya no admite postulaciones."
    return (
        f"El proyecto «{proyecto.nombre}» no está publicado para recibir "
        "postulaciones."
    )


def _anotar_estado_mostrado(postulacion):
    """Calcula el estado con el que se muestra una postulación.

    Parche de Etapa 2: una postulación ABIERTA cuyo proyecto está en
    'borrador', 'cancelado' o 'finalizado' se muestra como "rechazada", con
    el motivo del cierre. La fila NO se toca en la base de datos: la base
    todavía no tiene el cascade que cierre estas postulaciones (eso llega en
    Etapa 3, junto con el trigger de Postgres).

    `estado_mostrado` es el estado real salvo en ese caso. `motivo_cierre`
    queda vacío cuando el proyecto sigue siendo publicable.
    """
    proyecto = postulacion.vacante.proyecto
    no_publicable = proyecto.estado in ESTADOS_PROYECTO_NO_PUBLICABLE

    postulacion.motivo_cierre = (
        _motivo_proyecto_no_publicable(proyecto) if no_publicable else ""
    )
    postulacion.proyecto_no_publicable = no_publicable
    postulacion.proyecto_badge = ESTADO_BADGE.get(proyecto.estado, "")
    postulacion.proyecto_badge_label = proyecto.get_estado_display()

    if postulacion.estado in ESTADOS_POSTULACION_ABIERTA and no_publicable:
        postulacion.estado_mostrado = Postulacion.ESTADO_RECHAZADA
    else:
        postulacion.estado_mostrado = postulacion.estado
    return postulacion


@login_required
@require_POST
def postular_postulacion_view(request, pk):
    """
    Crea una postulación real del usuario a una vacante, con el Match Score
    congelado en el instante de postularse (CR-07, vía services.crear_postulacion).

    El servicio valida vacante abierta/activa, proyecto no cerrado y
    unicidad de postulación activa. La visibilidad del proyecto (borrador
    oculto a terceros) es regla de las vistas: aquí se aplica igual que en
    ProyectoDetailView, y el dueño nunca puede postularse a lo suyo.
    """
    vacante = get_object_or_404(
        Vacante.objects.select_related("proyecto"), pk=pk, es_activo=True
    )
    proyecto = vacante.proyecto
    destino = request.POST.get("next") or ""
    if not url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}
    ):
        destino = reverse("projects:project_detail", args=[proyecto.pk])

    # Borrador: no visible para terceros (misma regla que el detalle).
    if proyecto.estado == Proyecto.ESTADO_BORRADOR and proyecto.creador != request.user:
        raise Http404
    if proyecto.creador == request.user:
        messages.error(request, "No puedes postularte a tu propio proyecto.")
        return redirect(destino)

    try:
        postulacion = crear_postulacion(request.user, vacante)
    except PostulacionDuplicadaError:
        messages.error(
            request, "Ya tienes una postulación activa a esta vacante."
        )
        return redirect(destino)
    except VacanteNoPostulable:
        messages.error(request, "Esta vacante ya no admite postulaciones.")
        return redirect(destino)
    except ConfiguracionPesosNoDisponibleError:
        messages.error(
            request,
            "No se pudo calcular tu Match Score. Inténtalo más tarde.",
        )
        return redirect(destino)

    messages.success(
        request,
        "¡Postulación enviada! Tu Match Score para "
        f"«{vacante.titulo}» es de {floatformat(postulacion.match_score, 0)}%.",
    )
    return redirect(destino)


@login_required
def mis_postulaciones_view(request):
    """
    Vista para listar las postulaciones del usuario autenticado,
    optimizando la consulta con select_related y permitiendo filtros GET.

    El filtro por estado se aplica sobre `estado_mostrado`, no sobre el estado
    en la base de datos: una postulación abierta de un proyecto ya cerrado se
    muestra como "rechazada" (parche de Etapa 2) y por tanto no aparece
    bajo "Pendientes" ni "Preseleccionadas", sino bajo "Rechazadas".
    """
    estado_filtro = request.GET.get('estado')

    # Consulta optimizada (sin filtro es_activo por reglas de la tabla postulaciones)
    postulaciones = list(
        Postulacion.objects.filter(
            postulante_id=request.user.id
        ).select_related(
            'vacante__proyecto',
            'vacante',
            'pesos_usados'
        ).order_by('-postulado_en')
    )

    for postulacion in postulaciones:
        _anotar_estado_mostrado(postulacion)

    total = len(postulaciones)

    # Aplicar filtro si se seleccionó una categoría válida
    if estado_filtro in ESTADOS_FILTRABLES:
        postulaciones = [
            postulacion
            for postulacion in postulaciones
            if postulacion.estado_mostrado == estado_filtro
        ]

    context = {
        'postulaciones': postulaciones,
        'estado_actual': estado_filtro,
        # Para distinguir "no has postulate nunca" de "no tienes postulaciones
        # en este estado": la lista filtrada puede estar vacía aunque el
        # usuario tenga postulaciones en otras categorías.
        'total_postulaciones': total,
    }
    return render(request, 'applications/application_list.html', context)


@login_required
@require_POST
def retirar_postulacion_view(request, pk):
    """
    Retira (transición de estado a 'retirada') una postulación propia que
    esté en estado pendiente o preseleccionada. Nunca borra físicamente la
    fila (trigger trg_bloquear_borrado_postulaciones) ni toca cupos: solo
    una aceptación consume cupos, un retiro los libera implícitamente al
    desactivar la única postulación activa del usuario.
    """
    postulacion = get_object_or_404(
        Postulacion.objects.select_related("vacante__proyecto"),
        pk=pk,
        postulante=request.user,
    )

    if postulacion.estado not in ESTADOS_RETIRABLES:
        messages.error(
            request,
            "Solo puedes retirar postulaciones pendientes o preseleccionadas.",
        )
        return redirect("applications:mis_postulaciones")

    # El proyecto ya no admite postulaciones (borrador/cancelado/finalizado):
    # retirarla no tiene sentido. Es el mismo criterio que usa el listado para
    # mostrarla como "rechazada" (parche de Etapa 2).
    if postulacion.vacante.proyecto.estado in ESTADOS_PROYECTO_NO_PUBLICABLE:
        messages.error(
            request,
            "Esta postulación ya no está vigente: el proyecto no admite "
            "postulaciones.",
        )
        return redirect("applications:mis_postulaciones")

    try:
        with transaction.atomic():
            postulacion = Postulacion.objects.select_for_update().get(
                pk=postulacion.pk, postulante=request.user
            )

            if postulacion.estado not in ESTADOS_RETIRABLES:
                messages.error(
                    request,
                    "Solo puedes retirar postulaciones pendientes o preseleccionadas.",
                )
                return redirect("applications:mis_postulaciones")

            if postulacion.vacante.proyecto.estado in ESTADOS_PROYECTO_NO_PUBLICABLE:
                messages.error(
                    request,
                    "Esta postulación ya no está vigente: el proyecto no admite "
                    "postulaciones.",
                )
                return redirect("applications:mis_postulaciones")

            postulacion.estado = Postulacion.ESTADO_RETIRADA
            postulacion.decidido_por = request.user
            postulacion.decidido_en = timezone.now()
            postulacion.save(update_fields=["estado", "decidido_por", "decidido_en", "actualizado_en"])
    except Exception:
        messages.error(request, "Error al retirar la postulación.")
        return redirect("applications:mis_postulaciones")

    messages.success(request, "Tu postulación fue retirada.")
    return redirect("applications:mis_postulaciones")
