"""
URLconf raíz de DevMatch.
 
Archivo compartido. Cuando Squad B tenga listas sus vistas de accounts/
projects, agrega aquí sus `include(...)` (o pide al Integrador que lo
haga). No se incluyen todavía porque esas apps aún no tienen urlpatterns.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)