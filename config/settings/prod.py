"""Configuración de producción/demo.

Uso: DJANGO_SETTINGS_MODULE=config.settings.prod

Las variables de entorno nuevas son OPCIONALES y todas tienen default seguro,
as que un `.env` con las tres variables de siempre (DJANGO_SECRET_KEY,
DJANGO_ALLOWED_HOSTS, DATABASE_URL) sigue arrancando sin tocar nada.

Los guards de abajo leen `os.environ` directamente, no los valores ya
resueltos en base.py. Es deliberado: base.py rellena DJANGO_ALLOWED_HOSTS con
"127.0.0.1,localhost" y DJANGO_SECRET_KEY con una clave de desarrollo
conocida, así que comprobar las variables computadas nunca detectaría una
configuración ausente. Solo mirar el entorno real sí.
"""

import os

from .base import *  # noqa: F403

DEBUG = False

CLAVE_INSECURA = "django-insecure-solo-para-desarrollo-local"


def _exigida(nombre, motivo):
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise RuntimeError(
            f"{nombre} no esta definido y es obligatorio en produccion: {motivo}"
        )
    return valor


# --- Guards de arranque ------------------------------------------------------
# Si algo de esto falla, es preferible que el proceso no levante antes que
# servir trafico con una configuracion conocida como insegura.

SECRET_KEY = _exigida(
    "DJANGO_SECRET_KEY",
    "sin ella las sesiones, la cookie de autenticacion y los tokens de "
    "restablecimiento de contrasena quedan firmados con una clave publica "
    "del repositorio, y por tanto falsificables.",
)
if SECRET_KEY == CLAVE_INSECURA:
    raise RuntimeError(
        "DJANGO_SECRET_KEY sigue teniendo el valor de desarrollo por defecto. "
        "Genera una real con: python -c \"import secrets; "
        "print(secrets.token_urlsafe(50))\""
    )
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "DJANGO_SECRET_KEY es demasiado corta para produccion. "
        "Usa secrets.token_urlsafe(50)."
    )

# Default vacio a proposito: aqui si puede quedar vacio y eso debe ser un error.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "")  # noqa: F405
if not ALLOWED_HOSTS:
    raise RuntimeError(
        "DJANGO_ALLOWED_HOSTS no esta definido. En produccion es obligatorio: "
        "sin el, un atacante puede manipular la cabecera Host para envenenar "
        "los enlaces de restablecimiento de contrasena y la cache."
    )
if "*" in ALLOWED_HOSTS:
    raise RuntimeError(
        "DJANGO_ALLOWED_HOSTS no puede contener '*' en produccion."
    )

# --- Endurecimiento ----------------------------------------------------------

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)  # noqa: F405

# Solo si hay un proxy delante que termine TLS y reescriba la cabecera. Marcarlo
# sin proxy real permite falsificar la deteccion de HTTPS desde el cliente.
if env_bool("DJANGO_USE_X_FORWARDED_PROTO", False):  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Orígenes extras para CSRF si la app se sirve desde un dominio distinto al del
# formulario. Vacio = comportamiento por defecto de Django.
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")  # noqa: F405

# HSTS es pegajoso: una vez que un navegador lo ve, lo aplica a TODOS los
# subdominios y no hay vuelta atras. Por eso subdominios y preload están
# apagados por defecto y solo se activan a proposito.
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False)  # noqa: F405
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)  # noqa: F405

if SECURE_HSTS_PRELOAD and SECURE_HSTS_SECONDS < 31536000:
    raise RuntimeError(
        "DJANGO_HSTS_PRELOAD exige DJANGO_SECURE_HSTS_SECONDS >= 31536000 "
        "(1 ano). Los navegadores rechazan el preload por debajo de ese "
        "minimo y, mientras dura, no se puede revertir."
    )
if SECURE_HSTS_INCLUDE_SUBDOMAINS and SECURE_HSTS_SECONDS == 0:
    raise RuntimeError(
        "DJANGO_HSTS_INCLUDE_SUBDOMAINS no tiene sentido con "
        "DJANGO_SECURE_HSTS_SECONDS=0."
    )

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

# whitenoise sirve STATIC_ROOT sin depender de un web server (nginx) delante.
# Sin esto, ManifestStaticFilesStorage funciona pero el CSS construido
# (static/dist/output.css) daria 404 en el despliegue.
#
# Va solo en prod y no en base.py a proposito: en desarrollo no hace falta y
# tocar base.py obliga a avisar al equipo (ver DEVMATCH-ESTRUCTURA.md).
MIDDLEWARE = [  # noqa: F405
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE,  # noqa: F405
]