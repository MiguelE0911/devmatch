"""
URLconf raíz de DevMatch.
 
Archivo compartido. Cuando Squad B tenga listas sus vistas de accounts/
projects, agrega aquí sus `include(...)` (o pide al Integrador que lo
haga). No se incluyen todavía porque esas apps aún no tienen urlpatterns.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("", include("apps.projects.urls")),
    path("", include("apps.accounts.urls")),
    path("applications/", include("apps.applications.urls")),
]

# /media/ se sirve SIEMPRE con la vista estática de Django (en desarrollo ya
# lo hacía static(); en producción no hay nginx delante y whitenoise solo
# cubre estáticos, así que sin esto las imágenes subidas con Pillow darían
# 404). Suficiente para el demo del curso; ante un servidor real esto se
# reemplaza por un alias del proxy.
#
# login_not_required: LoginRequiredMiddleware exige login por defecto a toda
# vista, y las páginas públicas (detalle de proyecto, perfil) muestran estas
# imágenes a visitantes anónimos.
urlpatterns += [
    re_path(
        rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$",
        login_not_required(serve),
        {"document_root": settings.MEDIA_ROOT},
    ),
]