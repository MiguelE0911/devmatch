from django.contrib import admin

from .models import Resena


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ("autor", "destinatario", "proyecto", "calificacion", "es_activo", "creado_en")
    list_filter = ("es_activo", "calificacion")
    search_fields = ("autor__email", "destinatario__email", "proyecto__nombre")
    readonly_fields = ("creado_en",)