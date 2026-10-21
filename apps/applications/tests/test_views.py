from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.applications.models import Postulacion
from apps.matching.models import ConfiguracionPesosMatching
from apps.projects.models import Proyecto, Vacante
from apps.projects.tests.helpers import lleva_a

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


class PostularPostulacionTests(PostulacionesViewBase):
    """Flujo real de 'Postularme': crea la postulación con el snapshot del motor."""

    def setUp(self):
        super().setUp()
        # El proyecto nace en borrador (default del modelo); para este flujo lo
        # publicamos y reclutamos siguiendo la cadena válida de transiciones
        # (el trigger fn_validar_transicion_proyecto la exige).
        lleva_a(self.proyecto, Proyecto.ESTADO_RECLUTANDO)
        # La base ya creó una postulación pendiente del postulante a la vacante;
        # para el caso feliz necesitamos un usuario sin postulación previa.
        self.otro_postulante = Usuario.objects.create_user(
            "post2-view@devmatch.test", "post2-view", password="Clave-123!"
        )
        ConfiguracionPesosMatching.objects.create(
            nombre="Default",
            peso_habilidades=Decimal("0.35"),
            peso_nivel=Decimal("0.15"),
            peso_tecnologias=Decimal("0.30"),
            peso_experiencia=Decimal("0.10"),
            peso_disponibilidad=Decimal("0.10"),
            es_activo=True,
        )

    def _url(self, vacante=None):
        return reverse(
            "applications:postular", args=[(vacante or self.vacante).pk]
        )

    def test_requiere_login(self):
        respuesta = self.client.post(self._url())
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/ingresar/", respuesta.url)

    def test_get_no_esta_permitido(self):
        self.client.force_login(self.otro_postulante)
        self.assertEqual(self.client.get(self._url()).status_code, 405)

    def test_post_crea_postulacion_con_snapshot_del_motor(self):
        self.client.force_login(self.otro_postulante)
        respuesta = self.client.post(self._url())
        self.assertEqual(respuesta.status_code, 302)
        postulacion = Postulacion.objects.get(
            vacante=self.vacante, postulante=self.otro_postulante
        )
        self.assertEqual(postulacion.estado, Postulacion.ESTADO_PENDIENTE)
        # Snapshot real del motor: los 5 factores con {score, peso}.
        self.assertEqual(
            set(postulacion.match_factores.keys()),
            {
                "habilidades",
                "nivel",
                "tecnologias",
                "experiencia",
                "disponibilidad",
            },
        )
        for factor in postulacion.match_factores.values():
            self.assertIn("score", factor)
            self.assertIn("peso", factor)
        self.assertIsNotNone(postulacion.pesos_usados)
        self.assertEqual(postulacion.pesos_usados.es_activo, True)

    def test_duplicada_muestra_error_y_no_crea_otra(self):
        # self.postulante ya tiene una postulación pendiente a self.vacante.
        self.client.force_login(self.postulante)
        respuesta = self.client.post(self._url(), follow=True)
        self.assertEqual(
            Postulacion.objects.filter(
                vacante=self.vacante, postulante=self.postulante
            ).count(),
            1,
        )
        mensajes = [m.message for m in respuesta.context["messages"]]
        self.assertIn("Ya tienes una postulación activa a esta vacante.", mensajes)

    def test_vacante_inactiva_no_admite_postulacion(self):
        self.vacante.es_activo = False
        self.vacante.save(update_fields=["es_activo"])
        self.client.force_login(self.otro_postulante)
        respuesta = self.client.post(self._url())
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(
            Postulacion.objects.filter(
                vacante=self.vacante, postulante=self.otro_postulante
            ).exists()
        )

    def test_proyecto_finalizado_no_admite_postulacion(self):
        lleva_a(self.proyecto, Proyecto.ESTADO_FINALIZADO)
        self.client.force_login(self.otro_postulante)
        respuesta = self.client.post(self._url(), follow=True)
        self.assertEqual(
            Postulacion.objects.filter(
                vacante=self.vacante, postulante=self.otro_postulante
            ).count(),
            0,
        )
        mensajes = [m.message for m in respuesta.context["messages"]]
        self.assertIn("Esta vacante ya no admite postulaciones.", mensajes)

    def test_no_puede_postularse_a_proyecto_en_borrador(self):
        # No hay transición de vuelta a borrador, así que se crea un proyecto
        # nuevo (arranca en borrador por default del modelo).
        proyecto_borrador = Proyecto.objects.create(
            creador=self.creador,
            nombre="Proyecto Borrador",
            descripcion="Solo lo ve su creador.",
        )
        vacante_borrador = Vacante.objects.create(
            proyecto=proyecto_borrador,
            titulo="Backend",
            descripcion="Sin publicar.",
            cupos_totales=1,
        )
        self.client.force_login(self.otro_postulante)
        url = reverse("applications:postular", args=[vacante_borrador.pk])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_no_puede_postularse_a_su_propio_proyecto(self):
        self.client.force_login(self.creador)
        respuesta = self.client.post(self._url(), follow=True)
        mensajes = [m.message for m in respuesta.context["messages"]]
        self.assertIn("No puedes postularte a tu propio proyecto.", mensajes)
        self.assertFalse(
            Postulacion.objects.filter(
                vacante=self.vacante, postulante=self.creador
            ).exists()
        )

    def test_redirige_al_next_cuando_es_seguro(self):
        self.client.force_login(self.otro_postulante)
        destino = reverse("applications:mis_postulaciones")
        respuesta = self.client.post(self._url(), {"next": destino})
        self.assertRedirects(respuesta, destino)

    def test_next_malicioso_cae_al_detalle_del_proyecto(self):
        self.client.force_login(self.otro_postulante)
        respuesta = self.client.post(
            self._url(), {"next": "https://ejemplo-malicioso.test/"}
        )
        esperado = reverse("projects:project_detail", args=[self.proyecto.pk])
        self.assertRedirects(respuesta, esperado)
