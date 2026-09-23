from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.projects import models as m
from apps.projects import services as s

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
        self.proyecto.estado = m.Proyecto.ESTADO_FINALIZADO
        self.proyecto.save()
        with self.assertRaises(s.TransicionEstadoInvalida):
            s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_CANCELADO)

    def test_mismo_estado_no_lanza_error(self):
        resultado = s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_BORRADOR)
        self.assertEqual(resultado.estado, m.Proyecto.ESTADO_BORRADOR)

    def test_finalizar_registra_finalizado_en(self):
        self.proyecto.estado = m.Proyecto.ESTADO_EN_DESARROLLO
        self.proyecto.save()
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_FINALIZADO)
        self.proyecto.refresh_from_db()
        self.assertIsNotNone(self.proyecto.finalizado_en)

    def test_cancelar_registra_cancelado_en(self):
        s.cambiar_estado(self.proyecto, m.Proyecto.ESTADO_CANCELADO)
        self.proyecto.refresh_from_db()
        self.assertIsNotNone(self.proyecto.cancelado_en)
