"""Settings exclusivos para ejecutar migraciones.

Uso:
    DJANGO_SETTINGS_MODULE=config.settings.migrate python manage.py migrate

No usar este modulo para ``runserver`` ni para la aplicacion desplegada: usa el
rol duenio de las tablas, que puede alterar el esquema y desactivar triggers.
"""

import os

import dj_database_url

from .base import *  # noqa: F401,F403

_migration_url = os.environ.get("MIGRATION_DATABASE_URL", "").strip()
if not _migration_url:
    raise RuntimeError(
        "MIGRATION_DATABASE_URL no esta definida. Solo el rol de migraciones "
        "puede ejecutar migrate; la aplicacion debe usar DATABASE_URL."
    )

DATABASES = {
    "default": dj_database_url.parse(
        _migration_url,
        conn_max_age=0,
        conn_health_checks=True,
    )
}
