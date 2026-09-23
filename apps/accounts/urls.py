from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path(
        "ingresar/",
        login_not_required(
            LoginView.as_view(
                template_name="accounts/login.html",
                authentication_form=LoginForm,
                next_page="core:feed",
            )
        ),
        name="login",
    ),
    path(
        "registro/",
        login_not_required(views.RegistroView.as_view()),
        name="register",
    ),
    path(
        "salir/",
        LogoutView.as_view(next_page="accounts:login"),
        name="logout",
    ),
]