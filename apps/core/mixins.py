"""
Mixins reutilizables para vistas basadas en clase (CBV).

Los mixins de rol dependen de que `request.user` tenga los atributos
descritos en DEVMATCH-BD.md sección 5.1 (`es_admin`, etc.), definidos por
Squad A en accounts/models.py. Se usa getattr(..., False) para que este
archivo no truene mientras ese modelo todavía no existe.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Base para restringir una vista por rol. Las subclases deben
    sobreescribir `test_func()`. Si el usuario no cumple la condición,
    muestra una alerta (ver templates/partials/alerts.html) en vez de
    solo redirigir en silencio.
    """

    permission_denied_message = "No tienes permiso para acceder a esta sección."

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()


class AdminRequiredMixin(RoleRequiredMixin):
    """
    Restringe la vista solo a usuarios con `es_admin=True`.

    Cumple el requisito de ESP-V2 sección 6: "la capa de permisos del
    sistema debe bloquear automáticamente cualquier intento de acceder a
    creadores o colaboradores al panel administrativo".
    """

    permission_denied_message = "Esta sección es solo para administradores."

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and getattr(user, "es_admin", False)


# TODO (cuando exista apps.projects.models.Proyecto):
# class ProjectCreatorRequiredMixin(RoleRequiredMixin):
#     """Solo el creador_id del proyecto puede acceder (ver DEVMATCH-BD.md 5.2)."""
#     def test_func(self):
#         proyecto = self.get_object()
#         return proyecto.creador_id == self.request.user.id