from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase

from apps.projects.models import Proyecto, Vacante
from apps.projects.tests.helpers import lleva_a
from apps.reviews.models import Resena
from apps.teams.models import EquipoMembresia, Invitacion

Usuario = get_user_model()


class ResenaBase(TestCase):
    def setUp(self):
        self.autor = Usuario.objects.create_user(
            "autor-r@devmatch.test", "autor-r", password="Clave-123!"
        )
        self.destinatario = Usuario.objects.create_user(
            "destinatario-r@devmatch.test", "destinatario-r", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.autor, nombre="Demo", descripcion="desc"
        )
        lleva_a(self.proyecto, Proyecto.ESTADO_RECLUTANDO)
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto,
            titulo="Backend",
            descripcion="desc",
            cupos_totales=5,
        )
        self._miembro(self.destinatario)
        lleva_a(self.proyecto, Proyecto.ESTADO_FINALIZADO)

    def _miembro(self, usuario):
        """Registra a `usuario` como miembro real del proyecto.

        `trg_validar_resena` exige que autor y destinatario hayan sido
        miembros: cuenta el creador del proyecto o cualquiera con membresía en
        `equipos_membresias`. El check `chk_origen_membresia` exige que esa
        membresía venga de una postulación o de una invitación aceptada.
        """
        invitacion = Invitacion.objects.create(
            vacante=self.vacante,
            usuario_invitado=usuario,
            invitado_por=self.autor,
            estado=Invitacion.ESTADO_ACEPTADA,
        )
        return EquipoMembresia.objects.create(
            proyecto=self.proyecto,
            vacante=self.vacante,
            usuario=usuario,
            invitacion=invitacion,
        )

    def _resena(self, **kwargs):
        overrides = {
            "proyecto": self.proyecto,
            "autor": self.autor,
            "destinatario": self.destinatario,
            "calificacion": 4,
            "comentario": "Gran compañero",
        }
        overrides.update(kwargs)
        return Resena.objects.create(**overrides)


class ResenaContractTests(ResenaBase):
    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(Resena._meta.db_table, "resenas")
        columnas = {f.name: f.column for f in Resena._meta.fields}
        esperadas = {
            "proyecto": "proyecto_id",
            "autor": "autor_id",
            "destinatario": "destinatario_id",
            "calificacion": "calificacion",
            "comentario": "comentario",
            "es_activo": "es_activo",
            "desactivado_en": "desactivado_en",
            "desactivado_por": "desactivado_por_id",
            "creado_en": "creado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_defaults_coinciden_con_el_esquema(self):
        resena = self._resena()
        self.assertTrue(resena.es_activo)
        self.assertIsNone(resena.desactivado_en)
        self.assertIsNone(resena.desactivado_por)
        self.assertIsNotNone(resena.creado_en)


class ResenaIntegridadTests(ResenaBase):
    def test_calificacion_minima_y_maxima(self):
        otro = Usuario.objects.create_user(
            "tercero-c@devmatch.test", "tercero-c", password="Clave-123!"
        )
        self._resena(calificacion=1)
        self._miembro(otro)
        self._resena(calificacion=5, destinatario=otro)

    def test_rechaza_calificacion_fuera_de_rango(self):
        for calificacion in (0, 6):
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self._resena(calificacion=calificacion)

    def test_rechaza_autoresena(self):
        with self.assertRaises(IntegrityError):
            self._resena(autor=self.destinatario, destinatario=self.destinatario)

    def test_una_sola_resena_por_proyecto_autor_y_destinatario(self):
        self._resena()
        with self.assertRaises(IntegrityError):
            self._resena()

    def test_resena_de_dos_destinatarios_distintos_en_el_mismo_proyecto(self):
        otro = Usuario.objects.create_user(
            "tercero@devmatch.test", "tercero", password="Clave-123!"
        )
        self._resena()
        self._miembro(otro)
        self._resena(destinatario=otro)
        self.assertEqual(Resena.objects.count(), 2)

    def test_no_se_puede_borrar_fisicamente_un_proyecto_con_resenas(self):
        self._resena()
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self.proyecto.delete()
        self.assertEqual(Resena.objects.count(), 1)

    def test_no_se_puede_borrar_un_autor_con_resena(self):
        self._resena()
        # DatabaseError y no IntegrityError: el trigger de usuarios aborta con
        # SQLSTATE P0001, que Django no traduce a IntegrityError.
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self.autor.delete()

    def test_desactivacion_por_moderador_no_borra_la_evidencia(self):
        moderador = Usuario.objects.create_user(
            "moderador@devmatch.test", "moderador", password="Clave-123!"
        )
        resena = self._resena()
        resena.es_activo = False
        resena.desactivado_por = moderador
        resena.save()
        resena.refresh_from_db()
        self.assertFalse(resena.es_activo)
        self.assertEqual(resena.desactivado_por, moderador)