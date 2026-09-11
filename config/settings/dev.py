"""Configuración de desarrollo local. 
Uso: DJANGO_SETTINGS_MODULE=config.settings.dev"""
from .base import *

DEBUG = True

# Los hosts se toman de DJANGO_ALLOWED_HOSTS (base.py), por defecto
# "127.0.0.1,localhost". Cada quien puede sobrescribirlos en su .env.