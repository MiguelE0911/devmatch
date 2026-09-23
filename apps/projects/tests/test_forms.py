from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.projects.forms import ProyectoForm
from apps.projects.models import Proyecto

Usuario = get_user_model()


class ProyectoFormEstadoTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-form@devmatch.test", "creador-form", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def form_datos(self, **cambios):
        datos = {
            "nombre": self.proyecto.nombre,
            "descripcion": self.proyecto.descripcion,
            "logo_url": self.proyecto.logo_url or "",
            "estado": self.proyecto.estado,
        }
        datos.update(cambios)
        return datos

    def test_choices_solo_estado_actual_y_transiciones_validas(self):
        form = ProyectoForm(instance=self.proyecto)
        opciones = {v for v, _ in form.fields["estado"].choices}
        self.assertEqual(opciones, {"borrador", "publicado"})

    def test_transicion_valida_se_guarda(self):
        form = ProyectoForm(
            instance=self.proyecto,
            data=self.form_datos(estado=Proyecto.ESTADO_PUBLICADO),
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, Proyecto.ESTADO_PUBLICADO)

    def test_transicion_invalida_rechaza_y_no_guarda(self):
        form = ProyectoForm(
            instance=self.proyecto,
            data=self.form_datos(estado=Proyecto.ESTADO_FINALIZADO),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("estado", form.errors)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, Proyecto.ESTADO_BORRADOR)

    def test_finalizar_registra_finalizado_en(self):
        self.proyecto.estado = Proyecto.ESTADO_EN_DESARROLLO
        self.proyecto.save()
        form = ProyectoForm(
            instance=self.proyecto,
            data=self.form_datos(estado=Proyecto.ESTADO_FINALIZADO),
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, Proyecto.ESTADO_FINALIZADO)
        self.assertIsNotNone(self.proyecto.finalizado_en)

    def test_cancelado_no_es_una_opcion_editable(self):
        form = ProyectoForm(instance=self.proyecto)
        opciones = {v for v, _ in form.fields["estado"].choices}
        self.assertNotIn(Proyecto.ESTADO_CANCELADO, opciones)

    def test_estado_cancelado_explicito_se_rechaza(self):
        form = ProyectoForm(
            instance=self.proyecto,
            data=self.form_datos(estado=Proyecto.ESTADO_CANCELADO),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("estado", form.errors)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, Proyecto.ESTADO_BORRADOR)
        self.assertIsNone(self.proyecto.cancelado_en)

    def test_mismo_estado_no_escribe_timestamps(self):
        self.proyecto.estado = Proyecto.ESTADO_EN_DESARROLLO
        self.proyecto.save()
        self.proyecto.refresh_from_db()
        form = ProyectoForm(
            instance=self.proyecto,
            data=self.form_datos(estado=Proyecto.ESTADO_EN_DESARROLLO),
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.proyecto.refresh_from_db()
        self.assertIsNone(self.proyecto.finalizado_en)
        self.assertIsNone(self.proyecto.cancelado_en)