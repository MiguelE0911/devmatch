from django.db import OperationalError, connection
from django.shortcuts import render


def home(request):
    """Landing page pública de DevMatch."""
    return render(request, "core/home.html")


def health(request):
    """Health-check de conexión a la base de datos. (Ex-home de Etapa1)."""
    db_ok = True
    db_error = None

    try:
        connection.ensure_connection()
    except OperationalError as exc:
        db_ok = False
        db_error = str(exc)

    db_settings = connection.settings_dict

    context = {
        "db_ok": db_ok,
        "db_error": db_error,

        # Información de la conexión PostgreSQL
        "db_engine": db_settings.get("ENGINE", "").rsplit(".", 1)[-1],
        "db_name": db_settings.get("NAME"),
        "db_user": db_settings.get("USER"),
        "db_host": db_settings.get("HOST") or "localhost",
        "db_port": db_settings.get("PORT") or "5432",
    }

    return render(request, "core/health.html", context)