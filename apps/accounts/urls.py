from django.contrib.auth.views import LoginView
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path(
        "ingresar/",
        LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
            next_page="core:home",
        ),
        name="login",
    ),
    path("registro/", views.RegistroView.as_view(), name="register"),
]