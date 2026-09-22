from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path(
        "proyectos/<int:pk>/",
        views.ProyectoDetailView.as_view(),
        name="project_detail",
    ),
    path(
        "proyectos/<int:pk>/vacantes/nueva/",
        views.VacancyCreateView.as_view(),
        name="vacancy_create",
    ),
]