from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.projects import models as m
from apps.projects import services as s
from apps.projects.tests.helpers import lleva_a

Usuario = get_user_model()


class CambiarEstadoTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-servicios@devmatch.test", "creador-servicios", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def test_transicion_valida_actualiza_el_estado(self):
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_PUBLICADO)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, m.Proyecto.ESTADO_PUBLICADO)

    def test_transicion_invalida_lanza_excepcion_y_no_guarda(self):
        with self.assertRaises(s.TransicionEstadoInvalida):
            s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, m.Proyecto.ESTADO_BORRADOR)

    def test_estados_terminales_no_permiten_ninguna_transicion(self):
        lleva_a(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        with self.assertRaises(s.TransicionEstadoInvalida):
            s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_CANCELADO)

    def test_mismo_estado_no_lanza_error(self):
        resultado = s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_BORRADOR)
        self.assertEqual(resultado.estado, m.Proyecto.ESTADO_BORRADOR)

    def test_finalizar_registra_finalizado_en(self):
        lleva_a(self.proyecto, m.Proyecto.ESTADO_EN_DESARROLLO)
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        self.proyecto.refresh_from_db()
        self.assertIsNotNone(self.proyecto.finalizado_en)

    def test_cancelar_registra_cancelado_en(self):
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_CANCELADO)
        self.proyecto.refresh_from_db()
        self.assertIsNotNone(self.proyecto.cancelado_en)


class CerrarVacantesAlCerrarProyectoTests(TestCase):
    """Al cerrar el ciclo del proyecto (finalizado/cancelado) sus vacantes
    abiertas dejan de ser postulables: se marcan 'cancelada' (estado terminal,
    el trigger fn_actualizar_cupos_vacante no lo revierte)."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-vac@devmatch.test", "creador-vac", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def _vacante(self, **kwargs):
        return m.Vacante.objects.create(
            proyecto=self.proyecto,
            titulo="Backend",
            descripcion="desc",
            cupos_totales=2,
            **kwargs,
        )

    def test_finalizar_cierra_las_vacantes_abiertas(self):
        abierta = self._vacante()
        lleva_a(self.proyecto, m.Proyecto.ESTADO_EN_DESARROLLO)
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        abierta.refresh_from_db()
        self.assertEqual(abierta.estado, m.Vacante.ESTADO_CANCELADA)

    def test_cancelar_cierra_las_vacantes_abiertas(self):
        abierta = self._vacante()
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_CANCELADO)
        abierta.refresh_from_db()
        self.assertEqual(abierta.estado, m.Vacante.ESTADO_CANCELADA)

    def test_no_toca_las_vacantes_que_ya_no_estaban_abiertas(self):
        cubierta = self._vacante(
            estado=m.Vacante.ESTADO_CUBIERTA, cupos_ocupados=2
        )
        lleva_a(self.proyecto, m.Proyecto.ESTADO_EN_DESARROLLO)
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        cubierta.refresh_from_db()
        self.assertEqual(cubierta.estado, m.Vacante.ESTADO_CUBIERTA)


class PuedeAgregarVacantesTests(TestCase):
    """Solo se agregan vacantes mientras el proyecto no esté cerrado."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-agregar@devmatch.test", "creador-agregar", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def test_permite_los_estados_no_cerrados(self):
        for estado in (
            m.Proyecto.ESTADO_BORRADOR,
            m.Proyecto.ESTADO_PUBLICADO,
            m.Proyecto.ESTADO_RECLUTANDO,
            m.Proyecto.ESTADO_EQUIPO_COMPLETO,
            m.Proyecto.ESTADO_EN_DESARROLLO,
        ):
            with self.subTest(estado=estado):
                self.proyecto.estado = estado
                self.assertTrue(s.puede_agregar_vacantes(self.proyecto))

    def test_bloquea_los_estados_cerrados(self):
        for estado in (
            m.Proyecto.ESTADO_FINALIZADO,
            m.Proyecto.ESTADO_CANCELADO,
        ):
            with self.subTest(estado=estado):
                self.proyecto.estado = estado
                self.assertFalse(s.puede_agregar_vacantes(self.proyecto))


class PuedeAgregarImagenesTests(TestCase):
    """Solo `cancelado` impide agregar imágenes; `finalizado` sí lo permite."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-img@devmatch.test", "creador-img", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def test_permite_todos_los_estados_menos_cancelado(self):
        for estado in (
            m.Proyecto.ESTADO_BORRADOR,
            m.Proyecto.ESTADO_PUBLICADO,
            m.Proyecto.ESTADO_RECLUTANDO,
            m.Proyecto.ESTADO_EQUIPO_COMPLETO,
            m.Proyecto.ESTADO_EN_DESARROLLO,
            m.Proyecto.ESTADO_FINALIZADO,
        ):
            with self.subTest(estado=estado):
                self.proyecto.estado = estado
                self.assertTrue(s.puede_agregar_imagenes(self.proyecto))

    def test_bloquea_cancelado(self):
        self.proyecto.estado = m.Proyecto.ESTADO_CANCELADO
        self.assertFalse(s.puede_agregar_imagenes(self.proyecto))
