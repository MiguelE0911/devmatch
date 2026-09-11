"""Configuración de producción/demo. 
Uso: DJANGO_SETTINGS_MODULE=config.settings.prod"""
import os

from .base import *

DEBUG = False

if not ALLOWED_HOSTS:
    raise RuntimeError(
        "DJANGO_ALLOWED_HOSTS no está definido. En producción esto es "
        "obligatorio (no se permite '*' por seguridad)."
    )

# Endurecimiento típico de producción
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True) 
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}