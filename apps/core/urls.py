from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("home/", views.FeedView.as_view(), name="feed"),
    path("buscar/proyectos/", views.BuscarProyectosView.as_view(), name="buscar_proyectos"),
]