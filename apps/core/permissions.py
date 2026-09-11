"""
Helpers de permisos para vistas basadas en función (FBV) y templates.
Contraparte de mixins.py (que cubre las vistas basadas en clase).
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login


def es_administrador(user) -> bool:
    """True si el usuario está autenticado y tiene es_admin=True (DEVMATCH-BD.md 5.1)."""
    return bool(user and user.is_authenticated and getattr(user, "es_admin", False))


def admin_required(view_func):
    """Decorador equivalente a AdminRequiredMixin, para vistas de función."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not es_administrador(request.user):
            messages.error(request, "Esta sección es solo para administradores.")
            return redirect_to_login(request.get_full_path())
        return view_func(request, *args, **kwargs)

    return _wrapped


# TODO (Etapa 1, una vez existan apps.projects.models.Proyecto y la futura
# apps.teams.models.EquipoMembresia — ver DEVMATCH-ESTRUCTURA.md):
#
# Replicar aquí la verificación de "miembro real" de un proyecto descrita
# en DEVMATCH-BD.md sección 8.6 (la misma lógica que ya usa el trigger
# fn_validar_resena en la base de datos):
#
# def es_miembro_real(usuario, proyecto) -> bool:
#     if proyecto.creador_id == usuario.id:
#         return True
#     return proyecto.equipos_membresias.filter(
#         usuario=usuario, estado="activo"
#     ).exists()