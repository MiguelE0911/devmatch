from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.moderation.models import Reporte
from apps.projects.models import Proyecto

Usuario = get_user_model()


class ReporteBase(TestCase):
    def setUp(self):
        self.reportante = Usuario.objects.create_user(
            "reportante@devmatch.test", "reportante", password="Clave-123!"
        )
        self.reportado = Usuario.objects.create_user(
            "reportado@devmatch.test", "reportado", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.reportado, nombre="Demo", descripcion="desc"
        )

    def _reporte(self, **kwargs):
        overrides = {
            "reportante": self.reportante,
            "tipo_objetivo": Reporte.TIPO_OBJETIVO_PROYECTO,
            "proyecto_reportado": self.proyecto,
            "motivo": "Contenido inapropiado",
        }
        overrides.update(kwargs)
        return Reporte.objects.create(**overrides)


class ReporteContractTests(ReporteBase):
    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(Reporte._meta.db_table, "reportes")
        columnas = {f.name: f.column for f in Reporte._meta.fields}
        esperadas = {
            "reportante": "reportante_id",
            "tipo_objetivo": "tipo_objetivo",
            "proyecto_reportado": "proyecto_reportado_id",
            "usuario_reportado": "usuario_reportado_id",
            "motivo": "motivo",
            "descripcion": "descripcion",
            "estado": "estado",
            "decision": "decision",
            "resuelto_por": "resuelto_por_id",
            "resuelto_en": "resuelto_en",
            "creado_en": "creado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_tipos_objetivo_y_estados_coinciden_con_el_esquema_oficial(self):
        tipos = {valor for valor, _ in Reporte.TIPO_OBJETIVO_CHOICES}
        estados = {valor for valor, _ in Reporte.ESTADO_CHOICES}
        self.assertEqual(tipos, {"proyecto", "perfil", "conducta"})
        self.assertEqual(estados, {"pendiente", "en_revision", "resuelto", "descartado"})

    def test_defaults_coinciden_con_el_esquema(self):
        reporte = self._reporte()
        self.assertEqual(reporte.estado, Reporte.ESTADO_PENDIENTE)
        self.assertIsNotNone(reporte.creado_en)
        self.assertIsNone(reporte.resuelto_en)
        self.assertIsNone(reporte.resuelto_por)


class ReporteIntegridadTests(ReporteBase):
    def test_reporte_de_proyecto_valido(self):
        self._reporte()
        self.assertEqual(Reporte.objects.count(), 1)

    def test_reporte_de_perfil_y_de_conducta_validos(self):
        self._reporte(
            tipo_objetivo=Reporte.TIPO_OBJETIVO_PERFIL,
            proyecto_reportado=None,
            usuario_reportado=self.reportado,
        )
        self._reporte(
            tipo_objetivo=Reporte.TIPO_OBJETIVO_CONDUCTA,
            proyecto_reportado=None,
            usuario_reportado=self.reportado,
        )
        self.assertEqual(Reporte.objects.count(), 2)

    def test_proyecto_sin_objetivo_es_invalido(self):
        for tipo in (Reporte.TIPO_OBJETIVO_PROYECTO, Reporte.TIPO_OBJETIVO_PERFIL):
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self._reporte(
                        tipo_objetivo=tipo,
                        proyecto_reportado=None,
                        usuario_reportado=None,
                    )

    def test_objetivo_cruzado_es_invalido(self):
        proyectos = [
            (
                Reporte.TIPO_OBJETIVO_PERFIL,
                self.proyecto,
                None,
            ),
            (Reporte.TIPO_OBJETIVO_PROYECTO, None, self.reportado),
        ]
        for tipo, proyecto, usuario in proyectos:
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self._reporte(
                        tipo_objetivo=tipo,
                        proyecto_reportado=proyecto,
                        usuario_reportado=usuario,
                    )

    def test_reportante_opcional_y_set_null_si_se_borra(self):
        reporte = self._reporte()
        self.reportante.delete()
        reporte.refresh_from_db()
        self.assertIsNone(reporte.reportante)

    def test_el_reporte_se_borra_en_cascada_si_se_borra_el_proyecto_reportado(self):
        self._reporte()
        self.proyecto.delete()
        self.assertEqual(Reporte.objects.count(), 0)

    def test_resolver_reporte_persiste_decision_y_responsable(self):
        moderador = Usuario.objects.create_user(
            "moderador-r@devmatch.test", "moderador-r", password="Clave-123!"
        )
        reporte = self._reporte()
        reporte.estado = Reporte.ESTADO_RESUELTO
        reporte.decision = "Se ocultó la reseña."
        reporte.resuelto_por = moderador
        reporte.resuelto_en = timezone.now()
        reporte.save()
        reporte.refresh_from_db()
        self.assertEqual(reporte.estado, Reporte.ESTADO_RESUELTO)
        self.assertEqual(reporte.resuelto_por, moderador)
        self.assertIsNotNone(reporte.resuelto_en)