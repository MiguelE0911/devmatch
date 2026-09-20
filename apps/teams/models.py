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


class EquipoMembresia(models.Model):
    """
    Tabla `equipos_membresias`: composición del equipo de un proyecto.

    Reglas que garantiza el esquema oficial:
    - XOR chk_origen_membresia: la membresía entra EXACTAMENTE por una
      postulación aceptada o por una invitación aceptada, nunca ambas
      ni ninguna.
    - índice único parcial ux_membresia_activa_unica: solo una
      membresía 'activo' por (vacante, usuario). Un usuario retirado no
      se elimina: pasa a estado='retirado' (conserva historial).
    - Al insertar/retirar una membresía, el trigger
      trg_membresia_actualiza_cupos ajusta vacantes.cupos_ocupados y su
      estado — NO escribir esos campos manualmente.
    """

    ESTADO_ACTIVO = "activo"
    ESTADO_RETIRADO = "retirado"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_RETIRADO, "Retirado"),
    ]

    proyecto = models.ForeignKey(
        "projects.Proyecto",
        on_delete=models.CASCADE,
        related_name="membresias",
        db_column="proyecto_id",
    )
    vacante = models.ForeignKey(
        "projects.Vacante",
        on_delete=models.CASCADE,
        related_name="membresias",
        db_column="vacante_id",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="membresias",
        db_column="usuario_id",
    )
    postulacion = models.ForeignKey(
        "applications.Postulacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membresias",
        db_column="postulacion_id",
    )
    invitacion = models.ForeignKey(
        "Invitacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membresias",
        db_column="invitacion_id",
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO
    )
    ingreso_en = models.DateTimeField(auto_now_add=True)
    retiro_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "equipos_membresias"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(postulacion__isnull=False, invitacion__isnull=True)
                    | Q(postulacion__isnull=True, invitacion__isnull=False)
                ),
                name="chk_origen_membresia",
            ),
            models.UniqueConstraint(
                fields=["vacante", "usuario"],
                condition=Q(estado="activo"),
                name="ux_membresia_activa_unica",
            ),
        ]

    def __str__(self):
        origen = "postulación" if self.postulacion_id else "invitación"
        return f"Membresía de {self.usuario} en {self.vacante} ({origen})"