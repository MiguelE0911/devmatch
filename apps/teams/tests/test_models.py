from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.projects.models import Proyecto, Vacante
from apps.teams import models as m

Usuario = get_user_model()


class InvitacionBase(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-inv@devmatch.test", "creador-inv", password="Clave-123!"
        )
        self.invitado = Usuario.objects.create_user(
            "invitado@devmatch.test", "invitado", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )

    def _invitar(self, **extra):
        return m.Invitacion.objects.create(
            vacante=self.vacante,
            usuario_invitado=self.invitado,
            invitado_por=self.creador,
            **extra,
        )


class InvitacionContractTests(InvitacionBase):
    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(m.Invitacion._meta.db_table, "invitaciones")
        columnas = {f.name: f.column for f in m.Invitacion._meta.fields}
        esperadas = {
            "vacante": "vacante_id",
            "usuario_invitado": "usuario_invitado_id",
            "invitado_por": "invitado_por_id",
            "estado": "estado",
            "creado_en": "creado_en",
            "respondido_en": "respondido_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_no_lleva_es_activo(self):
        # Los estados terminales conservan el historial sin columna extra.
        nombre_cols = {f.name for f in m.Invitacion._meta.fields}
        self.assertNotIn("es_activo", nombre_cols)

    def test_estados_disponibles_coinciden_con_el_esquema_oficial(self):
        valores = {valor for valor, _ in m.Invitacion.ESTADO_CHOICES}
        self.assertEqual(valores, {"pendiente", "aceptada", "rechazada", "ignorada"})

    def test_defaults_coinciden_con_el_esquema(self):
        invitacion = self._invitar()
        self.assertEqual(invitacion.estado, m.Invitacion.ESTADO_PENDIENTE)
        self.assertIsNotNone(invitacion.creado_en)
        self.assertIsNone(invitacion.respondido_en)


class InvitacionIntegridadTests(InvitacionBase):
    def test_solo_una_invitacion_pendiente_por_vacante_y_usuario(self):
        self._invitar()
        with self.assertRaises(IntegrityError):
            self._invitar()

    def test_puede_invitar_de_nuevo_tras_un_rechazo(self):
        self._invitar(estado=m.Invitacion.ESTADO_RECHAZADA, respondido_en=None)
        self._invitar()
        self.assertEqual(m.Invitacion.objects.count(), 2)

    def test_puede_invitar_de_nuevo_tras_respondido_aceptada(self):
        self._invitar(estado=m.Invitacion.ESTADO_ACEPTADA)
        self._invitar()
        self.assertEqual(m.Invitacion.objects.count(), 2)

    def test_se_borra_en_cascada_si_se_borra_la_vacante(self):
        self._invitar()
        self.vacante.delete()
        self.assertEqual(m.Invitacion.objects.count(), 0)

    def test_se_borra_en_cascada_si_se_elimina_el_usuario_invitado(self):
        self._invitar()
        self.invitado.delete()
        self.assertEqual(m.Invitacion.objects.count(), 0)

    def test_no_se_puede_borrar_quien_envio_invitaciones(self):
        self._invitar()
        with self.assertRaises(IntegrityError):
            self.creador.delete()