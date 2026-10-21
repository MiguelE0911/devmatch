from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.applications.models import Postulacion

ESTADOS_RETIRABLES = (Postulacion.ESTADO_PENDIENTE, Postulacion.ESTADO_PRESELECCIONADA)


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
