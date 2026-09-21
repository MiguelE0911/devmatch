from django.contrib import admin

from .models import Postulacion


@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
    list_display = (
        "postulante",
        "vacante",
        "estado",
        "match_score",
        "postulado_en",
    )
    list_filter = ("estado",)
    search_fields = ("postulante__email", "postulante__username", "vacante__titulo")
    readonly_fields = ("postulado_en", "actualizado_en")