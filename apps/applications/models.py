from django.conf import settings
from django.db import models
from django.db.models import Q


class Postulacion(models.Model):
    """
    Tabla `postulaciones`: la postulación de un usuario a una vacante con
    el Match Score congelado (snapshot) en el momento exacto de aplicarse
    (CR-07). `match_factores` nunca se recalcula ni se sobrescribe.

    Reglas que garantiza el esquema oficial:
    - `match_score` entre 0 y 100 (CHECK).
    - índice único parcial ux_postulacion_activa_unica: solo una
      postulación en estado 'pendiente'/'preseleccionada' por
      (vacante, postulante). Volver a postularse tras un rechazo o
      retiro SÍ está permitido.
    - No lleva es_activo: el estado 'retirada' ya conserva el historial.
    """

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_PRESELECCIONADA = "preseleccionada"
    ESTADO_ACEPTADA = "aceptada"
    ESTADO_RECHAZADA = "rechazada"
    ESTADO_RETIRADA = "retirada"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PRESELECCIONADA, "Preseleccionada"),
        (ESTADO_ACEPTADA, "Aceptada"),
        (ESTADO_RECHAZADA, "Rechazada"),
        (ESTADO_RETIRADA, "Retirada"),
    ]

    vacante = models.ForeignKey(
        "projects.Vacante",
        on_delete=models.CASCADE,
        related_name="postulaciones",
        db_column="vacante_id",
    )
    postulante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="postulaciones",
        db_column="postulante_id",
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE
    )
    match_score = models.DecimalField(max_digits=5, decimal_places=2)
    match_factores = models.JSONField()
    pesos_usados = models.ForeignKey(
        "matching.ConfiguracionPesosMatching",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="+",
        db_column="pesos_usados_id",
    )
    decidido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="decidido_por_id",
    )
    motivo_decision = models.TextField(blank=True, null=True)
    postulado_en = models.DateTimeField(auto_now_add=True)
    decidido_en = models.DateTimeField(blank=True, null=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "postulaciones"
        constraints = [
            models.CheckConstraint(
                condition=Q(match_score__gte=0) & Q(match_score__lte=100),
                name="chk_match_score_rango",
            ),
            models.UniqueConstraint(
                fields=["vacante", "postulante"],
                condition=Q(estado__in=["pendiente", "preseleccionada"]),
                name="ux_postulacion_activa_unica",
            ),
        ]

    def __str__(self):
        return f"Postulación de {self.postulante} a {self.vacante}"