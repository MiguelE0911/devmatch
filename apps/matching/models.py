from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ConfiguracionPesosMatching(models.Model):
    """
    Tabla `configuracion_pesos_matching`: perfil de pesos del motor de
    matching, versionado y singleton.

    Reglas que garantiza el esquema oficial:
    - los 5 pesos deben sumar exactamente 1.000 (CHECK chk_pesos_suman_uno).
    - solo un registro puede tener es_activo=True a la vez
      (índice único parcial ux_un_solo_peso_activo).
    - aquí es_activo significa "es el perfil vigente", NO "ocultar sin
      borrar" como en el resto del esquema (ver DevMatch-BD, 5.3).
    """

    nombre = models.CharField(max_length=100)
    peso_habilidades = models.DecimalField(max_digits=4, decimal_places=3)
    peso_nivel = models.DecimalField(max_digits=4, decimal_places=3)
    peso_tecnologias = models.DecimalField(max_digits=4, decimal_places=3)
    peso_experiencia = models.DecimalField(max_digits=4, decimal_places=3)
    peso_disponibilidad = models.DecimalField(max_digits=4, decimal_places=3)
    vigente_desde = models.DateTimeField(auto_now_add=True)
    vigente_hasta = models.DateTimeField(blank=True, null=True)
    es_activo = models.BooleanField(default=True)

    class Meta:
        db_table = "configuracion_pesos_matching"
        constraints = [
            models.UniqueConstraint(
                fields=["es_activo"],
                condition=Q(es_activo=True),
                name="ux_un_solo_peso_activo",
            )
        ]
        verbose_name = "Configuración de pesos de matching"
        verbose_name_plural = "Configuraciones de pesos de matching"

    def clean(self):
        total = (
            self.peso_habilidades
            + self.peso_nivel
            + self.peso_tecnologias
            + self.peso_experiencia
            + self.peso_disponibilidad
        )
        if total != Decimal("1.000"):
            raise ValidationError("Los cinco pesos deben sumar exactamente 1.000.")

    def __str__(self):
        return self.nombre