import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# devmatch/config/settings/base.py -> devmatch/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carga las variables desde .env
load_dotenv(BASE_DIR / '.env')

def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")
 
 
def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]
 
 
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-solo-para-desarrollo-local",
)

DEBUG = False

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps propias
    "apps.core",
    "apps.accounts",
    "apps.projects",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Base de datos (PostgreSQL - Neon)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback para desarrollo local si todavía no existe DATABASE_URL. 
    DATABASES = { 
        "default": { 
            "ENGINE": "django.db.backends.postgresql", 
            "NAME": os.environ.get("DB_NAME", "devmatch"), 
            "USER": os.environ.get("DB_USER", "postgres"), 
            "PASSWORD": os.environ.get("DB_PASSWORD", ""), 
            "HOST": os.environ.get("DB_HOST", "localhost"), 
            "PORT": os.environ.get("DB_PORT", "5432"), 
        } 
    }

# --------------------------------------------------------------------------
# AUTH_USER_MODEL: modelo custom en apps/accounts (tabla `usuarios`). Debe
# declararse ANTES de la primera migración de la app — si se agrega después,
# Django no arranca. Archivo compartido: avisar en el chat antes de tocarlo.
# --------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.Usuario"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internacionalización
LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Archivos estáticos y media
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # usado solo por collectstatic en prod
 
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
 
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"