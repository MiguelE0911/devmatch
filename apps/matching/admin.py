from django.contrib import admin

from .models import ConfiguracionPesosMatching


@admin.register(ConfiguracionPesosMatching)
class ConfiguracionPesosMatchingAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "peso_habilidades",
        "peso_nivel",
        "peso_tecnologias",
        "peso_experiencia",
        "peso_disponibilidad",
        "es_activo",
        "vigente_desde",
    )
    list_filter = ("es_activo",)
    search_fields = ("nombre",)