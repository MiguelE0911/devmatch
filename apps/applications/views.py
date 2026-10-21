from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.applications.models import Postulacion

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