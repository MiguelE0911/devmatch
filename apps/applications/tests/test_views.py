from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.applications.models import Postulacion
from apps.projects.models import Proyecto, Vacante

Usuario = get_user_model()

FACTORES_SNAPSHOT = {
    "habilidades": {"score": 100.0, "peso": 0.35},
    "nivel": {"score": 66.67, "peso": 0.15},
    "tecnologias": {"score": 100.0, "peso": 0.30},
    "experiencia": {"score": 30.0, "peso": 0.10},
    "disponibilidad": {"score": 50.0, "peso": 0.10},
}


class PostulacionesViewBase(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-view@devmatch.test", "creador-view", password="Clave-123!"
        )
        self.postulante = Usuario.objects.create_user(
            "post-view@devmatch.test", "post-view", password="Clave-123!"
        )
        self.otro = Usuario.objects.create_user(
            "otro-view@devmatch.test", "otro-view", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )
        self.postulacion = Postulacion.objects.create(
            vacante=self.vacante,
            postulante=self.postulante,
            match_score=Decimal("86.00"),
            match_factores=FACTORES_SNAPSHOT,
        )


class MisPostulacionesListTests(PostulacionesViewBase):
    def test_requiere_login(self):
        respuesta = self.client.get(reverse("applications:mis_postulaciones"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/ingresar/", respuesta.url)

    def test_solo_muestra_las_propias(self):
        Postulacion.objects.create(
            vacante=self.vacante,
            postulante=self.otro,
            match_score=Decimal("10.00"),
            match_factores=FACTORES_SNAPSHOT,
        )
        self.client.force_login(self.postulante)
        respuesta = self.client.get(reverse("applications:mis_postulaciones"))
        self.assertEqual(respuesta.status_code, 200)
        lista = list(respuesta.context["postulaciones"])
        self.assertEqual(lista, [self.postulacion])

    def test_filtro_por_estado(self):
        self.postulacion.estado = Postulacion.ESTADO_ACEPTADA
        self.postulacion.save(update_fields=["estado"])
        self.client.force_login(self.postulante)
        respuesta = self.client.get(
            reverse("applications:mis_postulaciones"), {"estado": "aceptada"}
        )
        self.assertEqual(len(respuesta.context["postulaciones"]), 1)
        respuesta = self.client.get(
            reverse("applications:mis_postulaciones"), {"estado": "pendiente"}
        )
        self.assertEqual(len(respuesta.context["postulaciones"]), 0)


class RetirarPostulacionTests(PostulacionesViewBase):
    def _url(self):
        return reverse(
            "applications:retirar_postulacion", args=[self.postulacion.pk]
        )

    def test_requiere_login(self):
        respuesta = self.client.post(self._url())
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/ingresar/", respuesta.url)

    def test_get_no_esta_permitido(self):
        self.client.force_login(self.postulante)
        self.assertEqual(self.client.get(self._url()).status_code, 405)

    def test_retira_postulacion_propia(self):
        self.client.force_login(self.postulante)
        respuesta = self.client.post(self._url())
        self.assertRedirects(respuesta, reverse("applications:mis_postulaciones"))
        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_RETIRADA)
        self.assertEqual(self.postulacion.decidido_por, self.postulante)
        self.assertIsNotNone(self.postulacion.decidido_en)

    def test_no_borra_la_fila(self):
        self.client.force_login(self.postulante)
        self.client.post(self._url())
        self.assertTrue(
            Postulacion.objects.filter(pk=self.postulacion.pk).exists()
        )

    def test_no_puede_retirar_de_otro_usuario(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.post(self._url()).status_code, 404)
        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_PENDIENTE)

    def test_no_retira_estado_final(self):
        self.postulacion.estado = Postulacion.ESTADO_ACEPTADA
        self.postulacion.save(update_fields=["estado"])
        self.client.force_login(self.postulante)
        respuesta = self.client.post(self._url())
        self.assertRedirects(respuesta, reverse("applications:mis_postulaciones"))
        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_ACEPTADA)

    def test_retira_preseleccionada(self):
        self.postulacion.estado = Postulacion.ESTADO_PRESELECCIONADA
        self.postulacion.save(update_fields=["estado"])
        self.client.force_login(self.postulante)
        self.client.post(self._url())
        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_RETIRADA)
