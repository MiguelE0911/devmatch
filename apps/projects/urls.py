from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [

    path(
        "proyectos/crear/",
        views.ProyectoCreateView.as_view(),
        name="project_create",
    ),
    path(
        "proyectos/<int:pk>/",
        views.ProyectoDetailView.as_view(),
        name="project_detail",
    ),
    path(
        "proyectos/<int:pk>/editar/",
        views.ProyectoEditView.as_view(),
        name="project_edit",
    ),
    path(
        "proyectos/<int:pk>/eliminar/",
        views.ProyectoDeleteView.as_view(),
        name="project_delete",
    ),
    path(
        "proyectos/<int:pk>/vacantes/nueva/",
        views.VacancyCreateView.as_view(),
        name="vacancy_create",
    ),
    path(
        "vacantes/<int:pk>/editar/",
        views.VacancyUpdateView.as_view(),
        name="vacancy_edit",
    ),
    path(
        "vacantes/<int:pk>/eliminar/",
        views.VacancyDeleteView.as_view(),
        name="vacancy_delete",
    ),
    path(
        "proyectos/<int:pk>/galeria/editar/",
        views.ProyectoGaleriaEditView.as_view(),
        name="project_gallery_edit",
    ),
    path(
        "proyectos/media/<int:pk>/eliminar/",
        views.ProyectoMediaDeleteView.as_view(),
        name="media_delete",
    ),
    path(
        "proyectos/<int:pk>/galeria/ordenar/",
        views.ProyectoMediaReorderView.as_view(),
        name="media_reorder",
    ),
]