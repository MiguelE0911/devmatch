from django.conf import settings
from django.db import models
from django.db.models import Q


class Invitacion(models.Model):
    """
    Tabla `invitaciones`: invitación proactiva de un creador a un usuario
    para una vacante (CR-18, FASE 10).

    Reglas que garantiza el esquema oficial:
    - índice único parcial ux_invitacion_pendiente_unica: solo una
      invitación 'pendiente' por (vacante, usuario_invitado).
    - No lleva es_activo: los estados terminales (aceptada/rechazada/
      ignorada) ya conservan el historial sin columna extra.
    """

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ACEPTADA = "aceptada"
    ESTADO_RECHAZADA = "rechazada"
    ESTADO_IGNORADA = "ignorada"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_ACEPTADA, "Aceptada"),
        (ESTADO_RECHAZADA, "Rechazada"),
        (ESTADO_IGNORADA, "Ignorada"),
    ]

    vacante = models.ForeignKey(
        "projects.Vacante",
        on_delete=models.CASCADE,
        related_name="invitaciones",
        db_column="vacante_id",
    )
    usuario_invitado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invitaciones_recibidas",
        db_column="usuario_invitado_id",
    )
    invitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="invitaciones_enviadas",
        db_column="invitado_por_id",
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    respondido_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "invitaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["vacante", "usuario_invitado"],
                condition=Q(estado="pendiente"),
                name="ux_invitacion_pendiente_unica",
            )
        ]

    def __str__(self):
        return f"Invitación de {self.invitado_por} a {self.usuario_invitado} ({self.vacante})"