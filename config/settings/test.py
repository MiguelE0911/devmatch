"""Ajustes para CI y pruebas con PostgreSQL efímero.

En CI usa el PostgreSQL del job. Contra Neon, definir ``TEST_DATABASE_URL`` con
el endpoint directo y un rol que pueda crear la base ``test_*``; no usar el rol
de runtime de la aplicación. Aquí se desactiva el almacenamiento externo para
que ningún test suba archivos al bucket compartido.
"""

import os

import dj_database_url
from django.contrib.auth.hashers import PBKDF2PasswordHasher

from .base import *  # noqa: F401,F403

DEBUG = False

_test_database_url = os.environ.get("TEST_DATABASE_URL", "").strip()
if _test_database_url:
    DATABASES["default"] = dj_database_url.parse(
        _test_database_url,
        conn_max_age=0,
        conn_health_checks=True,
    )


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
