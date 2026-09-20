from django.contrib import admin

from .models import (
    Proyecto,
    ProyectoMedia,
    Vacante,
    VacanteHabilidadRequerida,
    VacanteTecnologiaRequerida,
)

# NOTA: VacanteHabilidadRequerida y VacanteTecnologiaRequerida NO se
# registran aquí, por el mismo motivo que las tablas puente de accounts:
# Django no permite registrar en el admin un modelo con clave primaria
# compuesta (CompositePrimaryKey). Si el Integrador necesita cargar/ver
# estos datos, usar loaddata/dumpdata o un comando de fixtures.


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "creador", "estado", "es_activo", "creado_en")
    list_filter = ("estado", "es_activo")
    search_fields = ("nombre", "creador__email", "creador__username")
    readonly_fields = (
        "finalizado_en",
        "cancelado_en",
        "creado_en",
        "actualizado_en",
    )


@admin.register(Vacante)
class VacanteAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "proyecto",
        "estado",
        "cupos_ocupados",
        "cupos_totales",
        "es_activo",
    )
    list_filter = ("estado", "es_activo")
    search_fields = ("titulo", "proyecto__nombre")
    # cupos_ocupados lo mantiene el trigger trg_membresia_actualiza_cupos
    # en la base real; no debe poder editarse a mano desde el admin.
    readonly_fields = ("cupos_ocupados", "creado_en", "actualizado_en")


@admin.register(ProyectoMedia)
class ProyectoMediaAdmin(admin.ModelAdmin):
    list_display = ("proyecto", "tipo", "orden", "es_activo")
    list_filter = ("tipo", "es_activo")
    search_fields = ("proyecto__nombre",)
