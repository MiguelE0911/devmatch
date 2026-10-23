"""Ajustes para CI y pruebas con PostgreSQL efímero.

No usar este módulo contra Neon: el runner de Django crea y destruye bases
``test_*``, y aquí se desactiva el almacenamiento externo para que ningún test
suba archivos al bucket compartido.
"""
from django.contrib.auth.hashers import PBKDF2PasswordHasher

from .base import *  # noqa: F401,F403

DEBUG = False


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """PBKDF2 con pocas iteraciones: mismo prefijo que el hasher real, pero rápido."""

    iterations = 1


# Los tests crean muchos usuarios. Mantener el algoritmo PBKDF2 (hay tests que
# verifican el prefijo del hash) pero con una sola iteración.
PASSWORD_HASHERS = ["config.settings.test.FastPBKDF2PasswordHasher"]

# Evita conexiones persistentes que interfieren con la creación/borrado de
# bases de datos del runner de tests (especialmente con --parallel).
DATABASES["default"]["CONN_MAX_AGE"] = 0

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Nunca tocar el bucket real, aunque el .env local tenga credenciales.
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_ENDPOINT_URL_S3 = ""
AWS_REGION = ""
NEON_STORAGE_BUCKET = ""
