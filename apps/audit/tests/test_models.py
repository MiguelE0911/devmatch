from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.audit.models import AuditoriaLog

Usuario = get_user_model()


class AuditoriaLogContractTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "auditor@devmatch.test", "auditor", password="Clave-123!"
        )

    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(AuditoriaLog._meta.db_table, "auditoria_logs")
        columnas = {f.name: f.column for f in AuditoriaLog._meta.fields}
        esperadas = {
            "usuario": "usuario_id",
            "accion": "accion",
            "tabla_afectada": "tabla_afectada",
            "registro_id": "registro_id",
            "detalle": "detalle",
            "creado_en": "creado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_registro_basico_con_detalle_json(self):
        registro = AuditoriaLog.objects.create(
            usuario=self.usuario,
            accion="postulacion_aceptada",
            tabla_afectada="postulaciones",
            registro_id=42,
            detalle={"estado": "aceptada", "score": 87},
        )
        self.assertIsNotNone(registro.creado_en)
        self.assertEqual(registro.detalle["score"], 87)
        self.assertEqual(str(registro), "postulacion_aceptada en postulaciones#42")

    def test_usuario_opcional_y_set_null_si_se_borra(self):
        registro = AuditoriaLog.objects.create(
            usuario=self.usuario,
            accion="sistema",
            tabla_afectada="proyectos",
            registro_id=1,
        )
        self.usuario.delete()
        registro.refresh_from_db()
        self.assertIsNone(registro.usuario)

    def test_registro_sin_usuario_ni_detalle(self):
        registro = AuditoriaLog.objects.create(
            accion="estado_proyecto",
            tabla_afectada="proyectos",
            registro_id=7,
        )
        self.assertIsNone(registro.usuario)
        self.assertIsNone(registro.detalle)