from django.contrib import admin

from .models import Reporte


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_objetivo",
        "estado",
        "motivo",
        "reportante",
        "proyecto_reportado",
        "usuario_reportado",
        "creado_en",
    )
    list_filter = ("estado", "tipo_objetivo")
    search_fields = ("motivo", "reportante__email", "usuario_reportado__email")
    readonly_fields = ("creado_en", "resuelto_en")