from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import Habilidad, Tecnologia
from apps.projects import models as m
from apps.projects import services as s
from apps.projects.tests.helpers import lleva_a

Usuario = get_user_model()


class VacanteBase(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-vac@devmatch.test", "creador-vac", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.python = Habilidad.objects.create(nombre="Python-vac")
        self.sql = Habilidad.objects.create(nombre="SQL-vac")
        self.django = Tecnologia.objects.create(nombre="Django-vac")

    def _crear(self, **overrides):
        datos = {
            "titulo": "Backend",
            "descripcion": "desc",
            "cupos_totales": 2,
            "habilidades": [self.python],
            "tecnologias": [self.django],
        }
        datos.update(overrides)
        return s.crear_vacante(self.proyecto, **datos)

    def _vacante_directa(self, **campos):
        """Vacante creada por ORM, para fijar estados/cupos que el servicio
        no asigna (los mantiene el trigger en producción)."""
        datos = {
            "proyecto": self.proyecto,
            "titulo": "Directa",
            "descripcion": "desc",
            "cupos_totales": 2,
        }
        datos.update(campos)
        return m.Vacante.objects.create(**datos)

    def _requisitos(self, vacante):
        habilidades = {
            p.habilidad_id for p in m.VacanteHabilidadRequerida.objects.filter(vacante=vacante)
        }
        tecnologias = {
            p.tecnologia_id for p in m.VacanteTecnologiaRequerida.objects.filter(vacante=vacante)
        }
        return habilidades, tecnologias


class CrearVacanteTests(VacanteBase):
    def test_crea_vacante_abierta_con_sus_requisitos(self):
        vacante = self._crear()
        vacante.refresh_from_db()
        self.assertEqual(vacante.estado, m.Vacante.ESTADO_ABIERTA)
        self.assertTrue(vacante.es_activo)
        self.assertEqual(vacante.cupos_ocupados, 0)
        self.assertEqual(
            self._requisitos(vacante), ({self.python.pk}, {self.django.pk})
        )

    def test_permite_el_alta_mientras_el_proyecto_no_esta_cerrado(self):
        for estado in (
            m.Proyecto.ESTADO_BORRADOR,
            m.Proyecto.ESTADO_PUBLICADO,
            m.Proyecto.ESTADO_RECLUTANDO,
        ):
            with self.subTest(estado=estado):
                lleva_a(self.proyecto, estado)
                self.assertIsNotNone(self._crear())

    def test_rechaza_el_alta_si_el_proyecto_esta_finalizado(self):
        lleva_a(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        with self.assertRaises(s.ProyectoNoAceptaVacantes):
            self._crear()
        self.assertEqual(m.Vacante.objects.count(), 0)

    def test_rechaza_el_alta_si_el_proyecto_esta_cancelado(self):
        lleva_a(self.proyecto, m.Proyecto.ESTADO_CANCELADO)
        with self.assertRaises(s.ProyectoNoAceptaVacantes) as ctx:
            self._crear()
        self.assertIn("cancelado", str(ctx.exception))
        self.assertEqual(m.Vacante.objects.count(), 0)

    def test_rollback_si_falla_la_sincronizacion_de_requisitos(self):
        """Si falla el último paso, no queda nada guardado: ni la vacante ni
        los requisitos que ya se habían escrito."""
        with mock.patch.object(
            s, "_sincronizar_tecnologias", side_effect=RuntimeError("falla")
        ):
            with self.assertRaises(RuntimeError):
                self._crear()
        self.assertEqual(m.Vacante.objects.count(), 0)
        self.assertEqual(m.VacanteHabilidadRequerida.objects.count(), 0)


class ActualizarVacanteTests(VacanteBase):
    def setUp(self):
        super().setUp()
        self.vacante = self._crear()

    def _editar(self, vacante=None, **overrides):
        datos = {
            "titulo": "Backend",
            "descripcion": "desc",
            "cupos_totales": 2,
            "habilidades": [self.python],
            "tecnologias": [self.django],
        }
        datos.update(overrides)
        return s.actualizar_vacante(vacante or self.vacante, **datos)

    def test_edita_los_datos_y_sincroniza_los_requisitos(self):
        self._editar(
            titulo="Backend Senior",
            cupos_totales=3,
            habilidades=[self.sql],
            tecnologias=[],
        )
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.titulo, "Backend Senior")
        self.assertEqual(self.vacante.cupos_totales, 3)
        self.assertEqual(self._requisitos(self.vacante), ({self.sql.pk}, set()))

    def test_abierta_a_cancelada(self):
        self._editar(estado=m.Vacante.ESTADO_CANCELADA)
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.estado, m.Vacante.ESTADO_CANCELADA)

    def test_reapertura_explicita_de_una_cancelada_con_cupos_libres(self):
        self._editar(estado=m.Vacante.ESTADO_CANCELADA)
        self._editar(estado=m.Vacante.ESTADO_ABIERTA)
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.estado, m.Vacante.ESTADO_ABIERTA)

    def test_una_cancelada_sigue_cancelada_si_solo_se_editan_datos(self):
        self._editar(estado=m.Vacante.ESTADO_CANCELADA)
        self._editar(titulo="Nuevo titulo", cupos_totales=5)
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.estado, m.Vacante.ESTADO_CANCELADA)

    def test_no_se_puede_reabrir_si_el_proyecto_esta_finalizado(self):
        self._editar(estado=m.Vacante.ESTADO_CANCELADA)
        lleva_a(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        with self.assertRaises(s.ProyectoNoAceptaVacantes):
            self._editar(estado=m.Vacante.ESTADO_ABIERTA)
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.estado, m.Vacante.ESTADO_CANCELADA)

    def test_no_se_puede_reabrir_una_vacante_sin_cupos_libres(self):
        llena = self._vacante_directa(
            cupos_totales=1, cupos_ocupados=1, estado=m.Vacante.ESTADO_CANCELADA
        )
        with self.assertRaises(s.TransicionVacanteInvalida):
            self._editar(llena, cupos_totales=1, estado=m.Vacante.ESTADO_ABIERTA)

    def test_cubierta_no_se_puede_elegir_a_mano(self):
        with self.assertRaises(s.TransicionVacanteInvalida):
            self._editar(estado=m.Vacante.ESTADO_CUBIERTA)
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.estado, m.Vacante.ESTADO_ABIERTA)

    def test_desde_cubierta_no_hay_cambios_manuales_de_estado(self):
        cubierta = self._vacante_directa(
            cupos_totales=1, cupos_ocupados=1, estado=m.Vacante.ESTADO_CUBIERTA
        )
        for destino in (m.Vacante.ESTADO_CANCELADA, m.Vacante.ESTADO_ABIERTA):
            with self.subTest(destino=destino):
                with self.assertRaises(s.TransicionVacanteInvalida):
                    self._editar(cubierta, cupos_totales=1, estado=destino)

    def test_no_se_puede_bajar_por_debajo_de_los_cupos_ocupados(self):
        con_miembros = self._vacante_directa(cupos_totales=3, cupos_ocupados=2)
        with self.assertRaises(s.VacanteInvalida):
            self._editar(con_miembros, cupos_totales=1)
        con_miembros.refresh_from_db()
        self.assertEqual(con_miembros.cupos_totales, 3)

    def test_subir_los_cupos_de_una_cubierta_la_vuelve_a_abrir(self):
        cubierta = self._vacante_directa(
            cupos_totales=1, cupos_ocupados=1, estado=m.Vacante.ESTADO_CUBIERTA
        )
        self._editar(cubierta, cupos_totales=2)
        cubierta.refresh_from_db()
        self.assertEqual(cubierta.estado, m.Vacante.ESTADO_ABIERTA)

    def test_bajar_los_cupos_hasta_los_ocupados_la_marca_cubierta(self):
        casi = self._vacante_directa(cupos_totales=3, cupos_ocupados=2)
        self._editar(casi, cupos_totales=2)
        casi.refresh_from_db()
        self.assertEqual(casi.estado, m.Vacante.ESTADO_CUBIERTA)

    def test_rollback_en_la_edicion_si_falla_la_sincronizacion(self):
        requisitos_antes = self._requisitos(self.vacante)
        with mock.patch.object(
            s, "_sincronizar_tecnologias", side_effect=RuntimeError("falla")
        ):
            with self.assertRaises(RuntimeError):
                self._editar(titulo="No debe guardarse", habilidades=[self.sql])
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.titulo, "Backend")
        self.assertEqual(self._requisitos(self.vacante), requisitos_antes)


class VacanteHelpersTests(SimpleTestCase):
    def _vacante(self, **campos):
        datos = {
            "estado": m.Vacante.ESTADO_ABIERTA,
            "es_activo": True,
            "cupos_totales": 2,
            "cupos_ocupados": 1,
        }
        datos.update(campos)
        return m.Vacante(**datos)

    def test_esta_abierta(self):
        self.assertTrue(self._vacante().esta_abierta)
        self.assertFalse(self._vacante(estado=m.Vacante.ESTADO_CUBIERTA).esta_abierta)
        self.assertFalse(self._vacante(estado=m.Vacante.ESTADO_CANCELADA).esta_abierta)
        self.assertFalse(self._vacante(es_activo=False).esta_abierta)

    def test_tiene_cupo_libre(self):
        self.assertTrue(self._vacante(cupos_ocupados=1).tiene_cupo_libre)
        self.assertFalse(self._vacante(cupos_ocupados=2).tiene_cupo_libre)


class VacanteVistasTests(VacanteBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.creador)

    def _datos(self, **overrides):
        datos = {"titulo": "Backend", "descripcion": "desc", "cupos_totales": 2}
        datos.update(overrides)
        return datos

    def test_alta_valida_crea_la_vacante_abierta(self):
        url = reverse("projects:vacancy_create", kwargs={"pk": self.proyecto.pk})
        response = self.client.post(
            url, self._datos(habilidades=[self.python.pk], tecnologias=[self.django.pk])
        )
        self.assertEqual(response.status_code, 302)
        vacante = m.Vacante.objects.get()
        self.assertEqual(vacante.estado, m.Vacante.ESTADO_ABIERTA)
        self.assertEqual(
            self._requisitos(vacante), ({self.python.pk}, {self.django.pk})
        )

    def test_alta_en_proyecto_finalizado_muestra_el_error_y_no_crea(self):
        lleva_a(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        url = reverse("projects:vacancy_create", kwargs={"pk": self.proyecto.pk})
        response = self.client.post(url, self._datos())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "el proyecto está finalizado")
        self.assertEqual(m.Vacante.objects.count(), 0)

    def test_la_edicion_persiste_el_cambio_de_estado(self):
        vacante = self._crear()
        url = reverse("projects:vacancy_edit", kwargs={"pk": vacante.pk})
        response = self.client.post(
            url, self._datos(estado=m.Vacante.ESTADO_CANCELADA)
        )
        self.assertEqual(response.status_code, 302)
        vacante.refresh_from_db()
        self.assertEqual(vacante.estado, m.Vacante.ESTADO_CANCELADA)

    def test_la_edicion_rechaza_elegir_cubierta(self):
        vacante = self._crear()
        url = reverse("projects:vacancy_edit", kwargs={"pk": vacante.pk})
        response = self.client.post(
            url, self._datos(estado=m.Vacante.ESTADO_CUBIERTA)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("estado", response.context["form"].errors)
        vacante.refresh_from_db()
        self.assertEqual(vacante.estado, m.Vacante.ESTADO_ABIERTA)