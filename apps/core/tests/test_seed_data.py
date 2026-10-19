"""
Fechas escalonadas de seed_data: orden, secuencia y ausencia de fechas futuras.

Ejecuta el comando contra la base de PRUEBAS de Django (nunca contra Neon) con
el reloj fijado, así que no depende de la hora a la que se corra.
"""
from datetime import datetime, timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.applications.models import Postulacion
from apps.projects.models import Proyecto, Vacante
from apps.teams.models import EquipoMembresia, Invitacion

# Tabla de la tarjeta: proyecto -> días atrás
DIAS_POR_PROYECTO = {
    "ResuMate": 3,
    "BrainTwist": 10,
    "PetMatch": 18,
    "GymLog": 27,
    "ClinVis": 40,
    "DevRoom": 55,
    "FitTrack": 68,
    "MarketAI": 80,
    "ViajeSeguro": 90,
}


def correr_seed(ahora):
    with mock.patch("django.utils.timezone.now", return_value=ahora):
        call_command("seed_data", stdout=StringIO())


def tomar_fechas():
    return {
        "usuarios": sorted(Usuario.objects.values_list("email", "creado_en"), key=repr),
        "proyectos": sorted(
            Proyecto.objects.values_list("nombre", "creado_en", "finalizado_en", "cancelado_en"),
            key=repr,
        ),
        "vacantes": sorted(
            Vacante.objects.values_list("proyecto__nombre", "titulo", "creado_en"), key=repr
        ),
        "postulaciones": sorted(
            Postulacion.objects.values_list(
                "vacante__proyecto__nombre",
                "vacante__titulo",
                "postulante__email",
                "postulado_en",
                "decidido_en",
            ),
            key=repr,
        ),
        "invitaciones": sorted(
            Invitacion.objects.values_list(
                "vacante__proyecto__nombre", "usuario_invitado__email", "creado_en", "respondido_en"
            ),
            key=repr,
        ),
        "membresias": sorted(
            EquipoMembresia.objects.values_list(
                "vacante__proyecto__nombre", "usuario__email", "ingreso_en"
            ),
            key=repr,
        ),
    }


class SeedFechasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ahora = timezone.now()
        correr_seed(cls.ahora)

    def test_el_seed_genero_todas_las_filas_esperadas(self):
        """El seed ignora en silencio los errores de membresías e invitaciones;
        esto evita que los demás tests pasen sobre una siembra incompleta."""
        self.assertEqual(Usuario.objects.count(), 5)
        self.assertEqual(Proyecto.objects.count(), 9)
        self.assertEqual(Vacante.objects.count(), 8)
        self.assertEqual(Postulacion.objects.count(), 10)
        self.assertEqual(Invitacion.objects.count(), 1)
        self.assertEqual(EquipoMembresia.objects.count(), 4)

    def test_cada_proyecto_tiene_los_dias_de_la_tarjeta(self):
        for proyecto in Proyecto.objects.all():
            marca = proyecto.nombre.split(" ")[0]
            self.assertEqual(
                self.ahora - proyecto.creado_en,
                timedelta(days=DIAS_POR_PROYECTO[marca]),
                marca,
            )

    def test_proyectos_quedan_ordenados_del_mas_reciente_al_mas_antiguo(self):
        marcas = [
            p.nombre.split(" ")[0] for p in Proyecto.objects.order_by("-creado_en")
        ]
        self.assertEqual(marcas, list(DIAS_POR_PROYECTO))

    def test_ninguna_fecha_cae_en_el_futuro(self):
        fechas = [
            valor
            for filas in tomar_fechas().values()
            for fila in filas
            for valor in fila
            if isinstance(valor, datetime)
        ]
        self.assertTrue(fechas)
        self.assertLessEqual(max(fechas), self.ahora)

    def test_la_secuencia_de_eventos_es_coherente(self):
        for proyecto in Proyecto.objects.select_related("creador"):
            self.assertLess(proyecto.creador.creado_en, proyecto.creado_en)
            if proyecto.estado == Proyecto.ESTADO_FINALIZADO:
                self.assertGreater(proyecto.finalizado_en, proyecto.creado_en)
                self.assertIsNone(proyecto.cancelado_en)
            elif proyecto.estado == Proyecto.ESTADO_CANCELADO:
                self.assertGreater(proyecto.cancelado_en, proyecto.creado_en)
                self.assertIsNone(proyecto.finalizado_en)
            else:
                self.assertIsNone(proyecto.finalizado_en)
                self.assertIsNone(proyecto.cancelado_en)

        for vacante in Vacante.objects.select_related("proyecto"):
            self.assertGreater(vacante.creado_en, vacante.proyecto.creado_en)

        for post in Postulacion.objects.select_related("vacante", "postulante"):
            self.assertGreater(post.postulado_en, post.vacante.creado_en)
            self.assertGreater(post.postulado_en, post.postulante.creado_en)
            if post.decidido_en is not None:
                self.assertGreater(post.decidido_en, post.postulado_en)

        for inv in Invitacion.objects.select_related("vacante"):
            self.assertGreater(inv.creado_en, inv.vacante.creado_en)
            self.assertGreater(inv.respondido_en, inv.creado_en)

        for membresia in EquipoMembresia.objects.select_related("postulacion", "invitacion"):
            origen = (
                membresia.postulacion.decidido_en
                if membresia.postulacion_id
                else membresia.invitacion.respondido_en
            )
            self.assertGreaterEqual(membresia.ingreso_en, origen)

    def test_las_filas_que_ya_existen_tambien_se_corrigen(self):
        """El fixup es incondicional: si el seed encuentra filas ya creadas
        (p. ej. en Neon, con las fechas viejas), las deja igual que las nuevas."""
        antes = tomar_fechas()

        # Simula filas sembradas antes de las fechas escalonadas: todo en "ahora".
        Usuario.objects.update(creado_en=self.ahora)
        Proyecto.objects.update(creado_en=self.ahora)
        Proyecto.objects.filter(estado=Proyecto.ESTADO_FINALIZADO).update(
            finalizado_en=self.ahora
        )
        Proyecto.objects.filter(estado=Proyecto.ESTADO_CANCELADO).update(
            cancelado_en=self.ahora
        )
        Vacante.objects.update(creado_en=self.ahora)
        Postulacion.objects.update(postulado_en=self.ahora)
        Postulacion.objects.exclude(decidido_en=None).update(decidido_en=self.ahora)
        Invitacion.objects.update(creado_en=self.ahora, respondido_en=self.ahora)
        EquipoMembresia.objects.update(ingreso_en=self.ahora)
        self.assertNotEqual(tomar_fechas(), antes)

        correr_seed(self.ahora)
        self.assertEqual(tomar_fechas(), antes)