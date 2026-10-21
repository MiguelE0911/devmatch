"""Tests de las vistas de gestión de postulaciones del dueño del proyecto
(preseleccionar / aprobar / rechazar) y del botón "Postularme" del detalle.

Cubre el contrato de Etapa 2:

- El botón "Postularme" del detalle apunta al flujo canónico
  `applications:postular` (y ya no existe `projects:postularse_vacante`).
- Un proyecto que NO está en 'reclutando' pero sigue abierto admite
  postulaciones (solo se excluyen 'borrador', 'cancelado' y 'finalizado').
- Aprobar exige una postulación 'preseleccionada', ocupa un cupo y solo una
  vez; cuando la vacante se llena pasa a 'cubierta'.
- Preseleccionar no reabre una postulación ya decidida.
- Rechazar deja al candidato en libertad de volver a postularse (el índice
  único `ux_postulacion_activa_unica` solo bloquea 'pendiente'/
  'preseleccionada').
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, resolve, reverse

from apps.applications.models import Postulacion
from apps.projects.models import Proyecto, Vacante
from apps.projects.views import (
    AprobarPostulacionView,
    RechazarPostulacionView,
)

Usuario = get_user_model()

FACTORES_SNAPSHOT = {
    "habilidades": {"score": 100.0, "peso": 0.35},
    "nivel": {"score": 66.67, "peso": 0.15},
    "tecnologias": {"score": 100.0, "peso": 0.30},
    "experiencia": {"score": 30.0, "peso": 0.10},
    "disponibilidad": {"score": 50.0, "peso": 0.10},
}


class PostulacionesViewsBase(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-post@devmatch.test", "creador-post", password="Clave-123!"
        )
        self.candidato = Usuario.objects.create_user(
            "candidato-post@devmatch.test", "candidato-post", password="Clave-123!"
        )
        self.intruso = Usuario.objects.create_user(
            "intruso-post@devmatch.test", "intruso-post", password="Clave-123!"
        )
        # Sin postulación: sirve para comprobar que el botón "Postularme"
        # aparece habilitado.
        self.candidato_libre = Usuario.objects.create_user(
            "libre-post@devmatch.test", "libre-post", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador,
            nombre="Demo",
            descripcion="desc",
            estado=Proyecto.ESTADO_RECLUTANDO,
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto,
            titulo="Backend",
            descripcion="desc",
            cupos_totales=3,
        )
        self.postulacion = Postulacion.objects.create(
            vacante=self.vacante,
            postulante=self.candidato,
            match_score=Decimal("86.00"),
            match_factores=FACTORES_SNAPSHOT,
        )

    def _preseleccionar(self, postulacion=None):
        postulacion = postulacion or self.postulacion
        postulacion.estado = Postulacion.ESTADO_PRESELECCIONADA
        postulacion.save(update_fields=["estado"])
        return postulacion


class RutasPostulacionTests(PostulacionesViewsBase):
    def test_url_rechazar_apunta_a_rechazar(self):
        url = reverse("projects:rechazar_postulacion", args=[self.postulacion.pk])
        self.assertTrue(url.endswith("/rechazar/"))
        self.assertIs(resolve(url).func.view_class, RechazarPostulacionView)

    def test_url_aprobar_apunta_a_aprobar(self):
        url = reverse("projects:aprobar_postulacion", args=[self.postulacion.pk])
        self.assertTrue(url.endswith("/aprobar/"))
        self.assertIs(resolve(url).func.view_class, AprobarPostulacionView)

    def test_ya_no_existe_la_ruta_propia_de_postularse(self):
        with self.assertRaises(NoReverseMatch):
            reverse("projects:postularse_vacante", args=[self.vacante.pk])


class AprobarPostulacionTests(PostulacionesViewsBase):
    def test_aprobar_pasa_a_aceptada_y_ocupa_cupo(self):
        self._preseleccionar()
        self.client.force_login(self.creador)

        respuesta = self.client.post(
            reverse("projects:aprobar_postulacion", args=[self.postulacion.pk])
        )

        self.assertEqual(respuesta.status_code, 302)
        self.postulacion.refresh_from_db()
        self.vacante.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_ACEPTADA)
        self.assertEqual(self.postulacion.decidido_por, self.creador)
        self.assertIsNotNone(self.postulacion.decidido_en)
        self.assertEqual(self.vacante.cupos_ocupados, 1)
        self.assertEqual(self.vacante.estado, Vacante.ESTADO_ABIERTA)

    def test_aprobar_ya_aceptada_no_ocupa_mas_cupo(self):
        self.postulacion.estado = Postulacion.ESTADO_ACEPTADA
        self.postulacion.save(update_fields=["estado"])
        self.vacante.cupos_ocupados = 1
        self.vacante.save(update_fields=["cupos_ocupados"])
        self.client.force_login(self.creador)

        self.client.post(
            reverse("projects:aprobar_postulacion", args=[self.postulacion.pk])
        )

        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.cupos_ocupados, 1)

    def test_aprobar_marca_la_vacante_cubierta(self):
        self.vacante.cupos_totales = 1
        self.vacante.save(update_fields=["cupos_totales"])
        self._preseleccionar()
        self.client.force_login(self.creador)

        self.client.post(
            reverse("projects:aprobar_postulacion", args=[self.postulacion.pk])
        )

        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.cupos_ocupados, 1)
        self.assertEqual(self.vacante.estado, Vacante.ESTADO_CUBIERTA)

    def test_aprobar_por_otro_dueno_no_hace_nada(self):
        self._preseleccionar()
        self.client.force_login(self.intruso)

        respuesta = self.client.post(
            reverse("projects:aprobar_postulacion", args=[self.postulacion.pk])
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("mis-proyectos", respuesta.url)
        self.postulacion.refresh_from_db()
        self.vacante.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_PRESELECCIONADA)
        self.assertEqual(self.vacante.cupos_ocupados, 0)

    def test_aprobar_sin_cupos_no_acepta(self):
        self.vacante.cupos_ocupados = self.vacante.cupos_totales
        self.vacante.save(update_fields=["cupos_ocupados"])
        self._preseleccionar()
        self.client.force_login(self.creador)

        self.client.post(
            reverse("projects:aprobar_postulacion", args=[self.postulacion.pk])
        )

        self.postulacion.refresh_from_db()
        self.vacante.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_PRESELECCIONADA)
        self.assertEqual(self.vacante.cupos_ocupados, self.vacante.cupos_totales)


class PreseleccionarPostulacionTests(PostulacionesViewsBase):
    def test_preseleccionar_pasa_a_preseleccionada(self):
        self.client.force_login(self.creador)

        respuesta = self.client.post(
            reverse("projects:preseleccionar_postulacion", args=[self.postulacion.pk])
        )

        self.assertEqual(respuesta.status_code, 302)
        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_PRESELECCIONADA)
        self.assertEqual(self.postulacion.decidido_por, self.creador)

    def test_preseleccionar_una_aceptada_no_la_reabre(self):
        self.postulacion.estado = Postulacion.ESTADO_ACEPTADA
        self.postulacion.save(update_fields=["estado"])
        self.client.force_login(self.creador)

        self.client.post(
            reverse("projects:preseleccionar_postulacion", args=[self.postulacion.pk])
        )

        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_ACEPTADA)

    def test_preseleccionar_por_otro_dueno_no_hace_nada(self):
        self.client.force_login(self.intruso)

        self.client.post(
            reverse("projects:preseleccionar_postulacion", args=[self.postulacion.pk])
        )

        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_PENDIENTE)


class RechazarPostulacionTests(PostulacionesViewsBase):
    def test_rechazar_pasa_a_rechazada(self):
        self.client.force_login(self.creador)

        respuesta = self.client.post(
            reverse("projects:rechazar_postulacion", args=[self.postulacion.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"ok": True})
        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_RECHAZADA)
        self.assertEqual(self.postulacion.decidido_por, self.creador)

    def test_rechazar_por_otro_dueno_responde_403(self):
        self.client.force_login(self.intruso)

        respuesta = self.client.post(
            reverse("projects:rechazar_postulacion", args=[self.postulacion.pk])
        )

        self.assertEqual(respuesta.status_code, 403)
        self.postulacion.refresh_from_db()
        self.assertEqual(self.postulacion.estado, Postulacion.ESTADO_PENDIENTE)


class BotonPostularmeTests(PostulacionesViewsBase):
    """El botón "Postularme" del detalle de proyecto."""

    def _detalle(self):
        return self.client.get(
            reverse("projects:project_detail", args=[self.proyecto.pk])
        )

    def test_postularme_usa_applications_postular(self):
        self.client.force_login(self.candidato_libre)

        respuesta = self._detalle()

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta, reverse("applications:postular", args=[self.vacante.pk])
        )
        self.assertContains(respuesta, 'name="next"')

    def test_boton_se_habilita_tras_un_rechazo(self):
        self.postulacion.estado = Postulacion.ESTADO_RECHAZADA
        self.postulacion.save(update_fields=["estado"])
        self.client.force_login(self.candidato)

        respuesta = self._detalle()

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta, reverse("applications:postular", args=[self.vacante.pk])
        )

    def test_boton_deshabilitado_con_postulacion_activa(self):
        self.client.force_login(self.candidato)

        respuesta = self._detalle()

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(
            respuesta, reverse("applications:postular", args=[self.vacante.pk])
        )
        self.assertContains(respuesta, "Ya tienes una postulación activa")

    def test_proyecto_no_reclutando_sigue_admitiendo_postulaciones(self):
        # Solo 'borrador', 'cancelado' y 'finalizado' cierran la puerta a
        # postulaciones: un proyecto 'publicado' todavía admite candidatos.
        # Se crea directamente en ese estado porque el trigger de transiciones
        # no permite ir de 'reclutando' a 'publicado'.
        proyecto = Proyecto.objects.create(
            creador=self.creador,
            nombre="Publicado",
            descripcion="desc",
            estado=Proyecto.ESTADO_PUBLICADO,
        )
        Vacante.objects.create(
            proyecto=proyecto,
            titulo="Frontend",
            descripcion="desc",
            cupos_totales=1,
        )
        self.client.force_login(self.candidato_libre)

        respuesta = self.client.get(
            reverse("projects:project_detail", args=[proyecto.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Postularme")
        vacante = proyecto.vacantes.get()
        self.assertContains(
            respuesta, reverse("applications:postular", args=[vacante.pk])
        )

    def test_proyecto_finalizado_no_admite_postulaciones(self):
        proyecto = Proyecto.objects.create(
            creador=self.creador,
            nombre="Cerrado",
            descripcion="desc",
            estado=Proyecto.ESTADO_FINALIZADO,
        )
        vacante = Vacante.objects.create(
            proyecto=proyecto,
            titulo="Backend",
            descripcion="desc",
            cupos_totales=1,
        )
        self.client.force_login(self.candidato_libre)

        respuesta = self.client.get(
            reverse("projects:project_detail", args=[proyecto.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(
            respuesta, reverse("applications:postular", args=[vacante.pk])
        )
