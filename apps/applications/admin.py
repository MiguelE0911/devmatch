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
    # `postulado_en` y `actualizado_en` los pone el sistema; el snapshot de
    # matching (score + factores) es inmutable: se calcula al postular y no
    # se recalcula aunque cambie el proyecto o el perfil (CR-07, CR-12).
    readonly_fields = (
        "postulado_en",
        "actualizado_en",
        "match_score",
        "match_factores",
    )