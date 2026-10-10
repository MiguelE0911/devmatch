from django.conf import settings
from django.contrib import messages
from django.contrib.auth import SESSION_KEY, logout
from django.shortcuts import redirect


class AccountStateMiddleware:
    """Cierra la sesión de cuentas bloqueadas o desactivadas.

    Django ya impide el login de cuentas con `is_active=False` y degrada a
    anónimo una sesión abierta (ModelBackend.get_user filtra por is_active).
    Pero esa sesión queda "colgante": la cookie sigue viva y, si el
    administrador reactiva la cuenta, el usuario vuelve a entrar sin pedir
    credenciales. Este middleware la cierra de forma explícita y le avisa.

    Cubre "proteger cuentas" y "protecciones de django" (feedback Etapa 1).
    Debe ir después de AuthenticationMiddleware (request.user) y de
    MessageMiddleware (para poder encolar el mensaje).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        autenticado = user is not None and user.is_authenticated

        # Un backend que no filtre is_active todavía dejaría pasar la sesión.
        if autenticado and not user.is_active:
            return self._cerrar_sesion(request)
        # Sesión colgante: no hay usuario autenticado pero la sesión apunta
        # a una cuenta que ya no puede entrar (bloqueada/desactivada).
        if not autenticado and request.session.get(SESSION_KEY):
            return self._cerrar_sesion(request)
        return self.get_response(request)

    @staticmethod
    def _cerrar_sesion(request):
        logout(request)
        messages.error(
            request,
            "Tu cuenta está bloqueada o desactivada. "
            "Si crees que es un error, contacta al administrador.",
        )
        return redirect(settings.LOGIN_URL)
