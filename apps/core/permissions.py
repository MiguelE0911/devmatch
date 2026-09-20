"""
Permisos y autorización a nivel servidor.

Contraparte de mixins.py (que cubre las vistas basadas en clase). Los
helpers `es_creador`/`creador_required` complementan a los mixins de rol
para cubrir el requisito CR-10: "validación de roles y permisos
directamente en el servidor, y no únicamente en la interfaz".
"""
from functools import wraps
from inspect import signature

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login


def es_creador(user, objeto) -> bool:
    """
    True si el usuario autenticado es el creador (`creador_id` en USUARIO,
    ver DEVMATCH-BD.md 5.2) del proyecto dueño de `objeto`.

    `objeto` puede ser un Proyecto o una subentidad que tenga FK
    `proyecto` (vacante, media, requisito, membresía...). Resuelve el
    proyecto dueño y compara `proyecto.creador_id` con `user.id`.
    """
    proyecto = _proyecto_de(objeto)
    return bool(
        user
        and user.is_authenticated
        and proyecto is not None
        and getattr(proyecto, "creador_id", None) == user.id
    )


def _proyecto_de(objeto):
    """
    Devuelve el Proyecto dueño de `objeto`. Si `objeto` ya es un Proyecto
    (tiene `creador_id`), lo devuelve; si no, resuelve la FK `proyecto`.
    """
    if objeto is None:
        return None
    if getattr(objeto, "creador_id", None) is not None:
        return objeto
    return getattr(objeto, "proyecto", None)


def creador_required(model, object_kwargs="pk"):
    """
    Decorador equivalente a ProjectCreatorRequiredMixin, para vistas de
    función. `model` es la clase del objeto dueño (Proyecto o subentidad).
    """

    def decorator(view_func):
        # Detecta si `view_func` es un método (primer parámetro `self`/`cls`)
        # para extraer el `request` correctamente y no confundirlo con la
        # instancia cuando se decora una vista basada en método.
        primer_parametro = next(iter(signature(view_func).parameters), None)
        es_metodo_de_vista = primer_parametro in ("self", "cls")

        @wraps(view_func)
        def _wrapped(*args, **kwargs):
            request = args[1] if es_metodo_de_vista else args[0]
            objeto = model.objects.filter(pk=kwargs.get(object_kwargs)).first()
            if not es_creador(request.user, objeto):
                _notificar_y_redirigir(request)
                return redirect_to_login(request.get_full_path())
            return view_func(*args, **kwargs)

        return _wrapped

    return decorator


def _notificar_y_redirigir(request):
    """
    Muestra un mensaje de error (si hay middleware de mensajes activo; si no,
    no truena) y devuelve la redirección al login. Última barrera a nivel
    servidor para CR-10: ni siquiera una petición sin permisos llega a la
    vista, aunque el middleware de mensajes no esté montado (tests).
    """
    try:
        messages.error(request, "Esta acción es solo para el creador del proyecto.")
    except Exception:
        pass
    return redirect_to_login(request.get_full_path())