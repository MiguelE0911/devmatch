from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.applications.models import Postulacion
from apps.projects.models import Proyecto, Vacante
from apps.teams import models as m

Usuario = get_user_model()


class EquipoMembresiaBase(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-mem@devmatch.test", "creador-mem", password="Clave-123!"
        )
        self.miembro = Usuario.objects.create_user(
            "miembro@devmatch.test", "miembro", password="Clave-123!"
        )
        self.postulante = Usuario.objects.create_user(
            "postulante-mem@devmatch.test", "postulante-mem", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )
        self.invitacion = m.Invitacion.objects.create(
            vacante=self.vacante,
            usuario_invitado=self.miembro,
            invitado_por=self.creador,
        )

    def _membresia_por_invitacion(self):
        return m.EquipoMembresia.objects.create(
            proyecto=self.proyecto,
            vacante=self.vacante,
            usuario=self.miembro,
            invitacion=self.invitacion,
        )

    def _postulacion_de(self, usuario):
        return Postulacion.objects.create(
            vacante=self.vacante,
            postulante=usuario,
            match_score=80,
            match_factores={"habilidades": 80},
        )


class EquipoMembresiaContractTests(EquipoMembresiaBase):
    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(m.EquipoMembresia._meta.db_table, "equipos_membresias")
        columnas = {f.name: f.column for f in m.EquipoMembresia._meta.fields}
        esperadas = {
            "proyecto": "proyecto_id",
            "vacante": "vacante_id",
            "usuario": "usuario_id",
            "postulacion": "postulacion_id",
            "invitacion": "invitacion_id",
            "estado": "estado",
            "ingreso_en": "ingreso_en",
            "retiro_en": "retiro_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_estados_disponibles_coinciden_con_el_esquema_oficial(self):
        valores = {valor for valor, _ in m.EquipoMembresia.ESTADO_CHOICES}
        self.assertEqual(valores, {"activo", "retirado"})

    def test_defaults_coinciden_con_el_esquema(self):
        membresia = self._membresia_por_invitacion()
        self.assertEqual(membresia.estado, m.EquipoMembresia.ESTADO_ACTIVO)
        self.assertIsNotNone(membresia.ingreso_en)
        self.assertIsNone(membresia.retiro_en)


class EquipoMembresiaIntegridadTests(EquipoMembresiaBase):
    def test_exige_exactamente_un_origen_postulacion_o_invitacion(self):
        with self.assertRaises(IntegrityError):
            m.EquipoMembresia.objects.create(
                proyecto=self.proyecto,
                vacante=self.vacante,
                usuario=self.miembro,
            )

    def test_no_acepta_postulacion_e_invitacion_a_la_vez(self):
        postulacion = self._postulacion_de(self.postulante)
        with self.assertRaises(IntegrityError):
            m.EquipoMembresia.objects.create(
                proyecto=self.proyecto,
                vacante=self.vacante,
                usuario=self.miembro,
                postulacion=postulacion,
                invitacion=self.invitacion,
            )

    def test_solo_una_membresia_activa_por_vacante_y_usuario(self):
        self._membresia_por_invitacion()
        postulacion = self._postulacion_de(self.miembro)
        with self.assertRaises(IntegrityError):
            m.EquipoMembresia.objects.create(
                proyecto=self.proyecto,
                vacante=self.vacante,
                usuario=self.miembro,
                postulacion=postulacion,
            )

    def test_se_puede_retirar_y_reingresar(self):
        primera = self._membresia_por_invitacion()
        primera.estado = m.EquipoMembresia.ESTADO_RETIRADO
        primera.save()
        self._membresia_por_invitacion()
        self.assertEqual(m.EquipoMembresia.objects.count(), 2)

    def test_se_borra_en_cascada_si_se_borra_el_proyecto(self):
        self._membresia_por_invitacion()
        self.proyecto.delete()
        self.assertEqual(m.EquipoMembresia.objects.count(), 0)

    def test_no_se_puede_borrar_un_miembro_con_membresia(self):
        self._membresia_por_invitacion()
        with self.assertRaises(IntegrityError):
            self.miembro.delete()