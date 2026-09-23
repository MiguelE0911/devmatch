from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Resena(models.Model):
    """
    Tabla `resenas`: reseñas verificadas entre miembros de un proyecto
    Finalizado (CR-20, FASE 8). El trigger trg_validar_resena (Postgres)
    impide crearla fuera de un proyecto finalizado y por quien no sea
    miembro real del proyecto (incluye al creador).

    Reglas que garantiza el esquema oficial:
    - calificacion entre 1 y 5 (CHECK chk_calificacion_rango).
    - autor <> destinatario (CHECK chk_no_autoresena).
    - UNIQUE (proyecto, autor, destinatario): una sola reseña por par.
    - es_activo=False permite a un admin ocultar reseñas ofensivas sin
      borrar la evidencia.
    """

    CALIFICACION_MINIMA = 1
    CALIFICACION_MAXIMA = 5

    proyecto = models.ForeignKey(
        "projects.Proyecto",
        on_delete=models.CASCADE,
        related_name="resenas",
        db_column="proyecto_id",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="resenas_escritas",
        db_column="autor_id",
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="resenas_recibidas",
        db_column="destinatario_id",
    )
    calificacion = models.SmallIntegerField()
    comentario = models.TextField(blank=True, null=True)
    es_activo = models.BooleanField(default=True)
    desactivado_en = models.DateTimeField(blank=True, null=True)
    desactivado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="desactivado_por_id",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "resenas"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(calificacion__gte=1) & Q(calificacion__lte=5)
                ),
                name="chk_calificacion_rango",
            ),
            models.CheckConstraint(
                condition=~Q(autor=F("destinatario")),
                name="chk_no_autoresena",
            ),
            models.UniqueConstraint(
                fields=["proyecto", "autor", "destinatario"],
                name="ux_resena_unica",
            ),
        ]

    def __str__(self):
        return f"Reseña de {self.autor} a {self.destinatario} ({self.calificacion}★)"