from django.contrib import admin

from .models import AuditoriaLog


@admin.register(AuditoriaLog)
class AuditoriaLogAdmin(admin.ModelAdmin):
    # Solo lectura: la tabla es de solo-append (trigger trg_inmutable_auditoria
    # bloquea UPDATE/DELETE en Postgres). El admin solo permite crear nuevos
    # registros, nunca editar ni borrar existentes.
    list_display = ("creado_en", "usuario", "accion", "tabla_afectada", "registro_id")
    list_filter = ("accion", "tabla_afectada")
    search_fields = ("tabla_afectada", "registro_id", "usuario__email")
    readonly_fields = (
        "usuario",
        "accion",
        "tabla_afectada",
        "registro_id",
        "detalle",
        "creado_en",
    )