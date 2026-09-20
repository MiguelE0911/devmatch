from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.applications import models as m
from apps.projects.models import Proyecto, Vacante

Usuario = get_user_model()


class PostulacionBase(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-post@devmatch.test", "creador-post", password="Clave-123!"
        )
        self.postulante = Usuario.objects.create_user(
            "postulante@devmatch.test", "postulante", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )

    def _postular(self, match_score=Decimal("87.50"), **extra):
        return m.Postulacion.objects.create(
            vacante=self.vacante,
            postulante=self.postulante,
            match_score=match_score,
            match_factores={"habilidades": 90, "nivel": 80},
            **extra,
        )


class PostulacionContractTests(PostulacionBase):
    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(m.Postulacion._meta.db_table, "postulaciones")
        columnas = {f.name: f.column for f in m.Postulacion._meta.fields}
        esperadas = {
            "vacante": "vacante_id",
            "postulante": "postulante_id",
            "estado": "estado",
            "match_score": "match_score",
            "match_factores": "match_factores",
            "pesos_usados": "pesos_usados_id",
            "decidido_por": "decidido_por_id",
            "motivo_decision": "motivo_decision",
            "postulado_en": "postulado_en",
            "decidido_en": "decidido_en",
            "actualizado_en": "actualizado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_no_lleva_es_activo(self):
        # El estado 'retirada' juega el rol de "ocultar sin borrar".
        nombre_cols = {f.name for f in m.Postulacion._meta.fields}
        self.assertNotIn("es_activo", nombre_cols)

    def test_estados_disponibles_coinciden_con_el_esquema_oficial(self):
        valores = {valor for valor, _ in m.Postulacion.ESTADO_CHOICES}
        self.assertEqual(
            valores, {"pendiente", "preseleccionada", "aceptada", "rechazada", "retirada"}
        )

    def test_defaults_coinciden_con_el_esquema(self):
        postulacion = self._postular()
        self.assertEqual(postulacion.estado, m.Postulacion.ESTADO_PENDIENTE)
        self.assertIsNotNone(postulacion.postulado_en)
        self.assertIsNone(postulacion.decidido_en)
        self.assertIsNone(postulacion.motivo_decision)


class PostulacionIntegridadTests(PostulacionBase):
    def test_match_score_fuera_de_rango_rechazado_por_la_bd(self):
        with self.assertRaises(IntegrityError):
            self._postular(match_score=Decimal("100.01"))

    def test_solo_una_postulacion_activa_por_vacante_y_postulante(self):
        self._postular()
        with self.assertRaises(IntegrityError):
            self._postular()

    def test_puede_repentirse_despues_de_un_rechazo(self):
        self._postular(estado=m.Postulacion.ESTADO_RECHAZADA)
        self._postular(estado=m.Postulacion.ESTADO_PENDIENTE)
        self.assertEqual(m.Postulacion.objects.count(), 2)

    def test_puede_volver_a_postularse_tras_retirarse(self):
        self._postular(estado=m.Postulacion.ESTADO_RETIRADA)
        self._postular()
        self.assertEqual(m.Postulacion.objects.count(), 2)

    def test_snapshot_de_factores_se_persiste_sin_sobrescribirse(self):
        postulacion = self._postular()
        postulacion.refresh_from_db()
        self.assertEqual(postulacion.match_factores, {"habilidades": 90, "nivel": 80})

    def test_se_borra_en_cascada_si_se_borra_la_vacante(self):
        self._postular()
        self.vacante.delete()
        self.assertEqual(m.Postulacion.objects.count(), 0)

    def test_no_se_puede_borrar_un_postulante_con_postulaciones(self):
        self._postular()
        with self.assertRaises(IntegrityError):
            self.postulante.delete()