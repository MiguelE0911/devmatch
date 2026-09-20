from django.conf import settings
from django.db import models
from django.db.models import Q


class Reporte(models.Model):
    """
    Tabla `reportes`: denuncias de moderación (CR-18, FASE 8).

    Reglas que garantiza el esquema oficial:
    - XOR chk_objetivo_reporte: si el objetivo es 'proyecto' solo se
      setea proyecto_reportado; si es 'perfil' o 'conducta' solo
      usuario_reportado.
    - estado permite pendiente / en_revision / resuelto / descartado.
      No lleva es_activo: 'descartado' cumple ese rol; el trigger
      trg_bloquear_borrado_reportes impide borrar físicamente un
      reporte (es evidencia de una decisión de moderación).
    """

    TIPO_OBJETIVO_PROYECTO = "proyecto"
    TIPO_OBJETIVO_PERFIL = "perfil"
    TIPO_OBJETIVO_CONDUCTA = "conducta"
    TIPO_OBJETIVO_CHOICES = [
        (TIPO_OBJETIVO_PROYECTO, "Proyecto"),
        (TIPO_OBJETIVO_PERFIL, "Perfil"),
        (TIPO_OBJETIVO_CONDUCTA, "Conducta"),
    ]

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_EN_REVISION = "en_revision"
    ESTADO_RESUELTO = "resuelto"
    ESTADO_DESCARTADO = "descartado"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_EN_REVISION, "En revisión"),
        (ESTADO_RESUELTO, "Resuelto"),
        (ESTADO_DESCARTADO, "Descartado"),
    ]

    reportante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_hechos",
        db_column="reportante_id",
    )
    tipo_objetivo = models.CharField(max_length=20, choices=TIPO_OBJETIVO_CHOICES)
    proyecto_reportado = models.ForeignKey(
        "projects.Proyecto",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reportes",
        db_column="proyecto_reportado_id",
    )
    usuario_reportado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reportes_recibidos",
        db_column="usuario_reportado_id",
    )
    motivo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    decision = models.TextField(blank=True, null=True)
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="resuelto_por_id",
    )
    resuelto_en = models.DateTimeField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reportes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        tipo_objetivo__in=["perfil", "conducta"],
                        proyecto_reportado__isnull=True,
                        usuario_reportado__isnull=False,
                    )
                    | Q(
                        tipo_objetivo="proyecto",
                        proyecto_reportado__isnull=False,
                        usuario_reportado__isnull=True,
                    )
                ),
                name="chk_objetivo_reporte",
            ),
        ]

    def __str__(self):
        objetivo = self.proyecto_reportado or self.usuario_reportado
        return f"Reporte de {self.tipo_objetivo} ({objetivo}) — {self.estado}"