from django.contrib import admin

from .models import EquipoMembresia, Invitacion


@admin.register(Invitacion)
class InvitacionAdmin(admin.ModelAdmin):
    list_display = ("usuario_invitado", "vacante", "estado", "creado_en")
    list_filter = ("estado",)
    search_fields = ("usuario_invitado__email", "vacante__titulo")
    readonly_fields = ("creado_en",)


@admin.register(EquipoMembresia)
class EquipoMembresiaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "vacante", "proyecto", "estado", "ingreso_en")
    list_filter = ("estado",)
    search_fields = ("usuario__email", "proyecto__nombre")
    readonly_fields = ("ingreso_en",)