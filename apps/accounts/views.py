from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

from .forms import RegistroForm
from .models import Usuario


class RegistroView(CreateView):
    """Alta de cuenta pública. Al terminar redirige a login con un mensaje.

    Solo crea el Usuario (es_activo=True, es_admin=False por default del
    modelo). El Perfil técnico se completa después (profile_form).
    """

    model = Usuario
    form_class = RegistroForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "¡Cuenta creada! Iniciá sesión con tu correo para continuar.",
        )
        return response