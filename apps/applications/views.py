from django.contrib import messages
from django.contrib.auth.decorators import login_required
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

ESTADOS_RETIRABLES = (Postulacion.ESTADO_PENDIENTE, Postulacion.ESTADO_PRESELECCIONADA)


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
    """
    estado_filtro = request.GET.get('estado')

    # Consulta optimizada (sin filtro es_activo por reglas de la tabla postulaciones)
    postulaciones = Postulacion.objects.filter(
        postulante_id=request.user.id
    ).select_related(
        'vacante__proyecto',
        'vacante',
        'pesos_usados'
    ).order_by('-postulado_en')

    # Aplicar filtro si se seleccionó una categoría válida
    if estado_filtro in ['pendiente', 'preseleccionada', 'aceptada']:
        postulaciones = postulaciones.filter(estado=estado_filtro)

    context = {
        'postulaciones': postulaciones,
        'estado_actual': estado_filtro,
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
        Postulacion, pk=pk, postulante=request.user
    )

    if postulacion.estado not in ESTADOS_RETIRABLES:
        messages.error(
            request,
            "Solo puedes retirar postulaciones pendientes o preseleccionadas.",
        )
        return redirect("applications:mis_postulaciones")

    postulacion.estado = Postulacion.ESTADO_RETIRADA
    postulacion.decidido_por = request.user
    postulacion.decidido_en = timezone.now()
    postulacion.save(update_fields=["estado", "decidido_por", "decidido_en", "actualizado_en"])

    messages.success(request, "Tu postulación fue retirada.")
    return redirect("applications:mis_postulaciones")
