from django.conf import settings
from django.db import models


class AuditoriaLog(models.Model):
    """
    Tabla `auditoria_logs`: trazabilidad de decisiones críticas
    (CR-17, FASE 8). Es de SOLO-APPEND:
    - Postgres bloquea UPDATE y DELETE con el trigger
      trg_inmutable_auditoria (fn_inmutable_auditoria).
    - Desde Django, por consistencia, NO usar .update() ni .delete()
      sobre esta tabla; solo crear registros nuevos. El admin la
      registra con todos los campos en solo lectura.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="usuario_id",
    )
    accion = models.CharField(max_length=100)
    tabla_afectada = models.CharField(max_length=100)
    registro_id = models.BigIntegerField()
    detalle = models.JSONField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auditoria_logs"
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"

    def __str__(self):
        return f"{self.accion} en {self.tabla_afectada}#{self.registro_id}"