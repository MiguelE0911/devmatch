"""
Fechas escalonadas de seed_data: orden, secuencia y ausencia de fechas futuras,
más invariantes de estado (tarjeta #36): el seed nunca deja vacantes abiertas
ni interacciones activas en proyectos cerrados, ni destruye vacantes 'cubierta'.

Ejecuta el comando contra la base de PRUEBAS de Django (nunca contra Neon) con
el reloj fijado, así que no depende de la hora a la que se corra.
"""
from datetime import datetime, timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db.models import F
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.applications.models import Postulacion
from apps.projects import services as services_proyectos
from apps.projects.models import Proyecto, Vacante
from apps.teams.models import EquipoMembresia, Invitacion

# Tabla de la tarjeta: proyecto -> días atrás
DIAS_POR_PROYECTO = {
    "ResuMate": 3,
    "BrainTwist": 10,
    "DevNotes": 14,
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
        self.assertEqual(Proyecto.objects.count(), 10)
        self.assertEqual(Vacante.objects.count(), 9)
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


class SeedInvariantesEstadoTests(TestCase):
    """Invariantes de la tarjeta #36: el seed no produce variaciones que los
    gates actuales de estado impiden reproducir en la interfaz."""

    CERRADOS = (Proyecto.ESTADO_FINALIZADO, Proyecto.ESTADO_CANCELADO)

    @classmethod
    def setUpTestData(cls):
        cls.ahora = timezone.now()
        correr_seed(cls.ahora)

    def test_no_hay_vacantes_abiertas_en_proyectos_cerrados(self):
        imposibles = Vacante.objects.filter(
            estado=Vacante.ESTADO_ABIERTA,
            proyecto__estado__in=self.CERRADOS,
        )
        self.assertFalse(imposibles.exists(), list(imposibles))

    def test_no_hay_interacciones_activas_en_proyectos_cerrados(self):
        activas = Postulacion.objects.filter(
            estado__in=[Postulacion.ESTADO_PENDIENTE, Postulacion.ESTADO_PRESELECCIONADA],
            vacante__proyecto__estado__in=self.CERRADOS,
        )
        self.assertFalse(activas.exists(), list(activas))

    def test_borrador_seediado_con_vacante_abierta(self):
        borrador = Proyecto.objects.get(nombre__startswith="DevNotes")
        self.assertEqual(borrador.estado, Proyecto.ESTADO_BORRADOR)
        vacante = Vacante.objects.get(proyecto=borrador)
        self.assertEqual(vacante.estado, Vacante.ESTADO_ABIERTA)
        self.assertEqual(vacante.cupos_totales, 1)

    def test_doble_corrida_no_descubre_vacantes_llenas(self):
        """La 2ª corrida no fuerza 'abierta' sobre vacantes llenadas por el
        trigger de cupos (GymLog 1/1 y BrainTwist QA 1/1)."""
        gymlog = Vacante.objects.get(
            proyecto__nombre__startswith="GymLog", titulo="Frontend Developer"
        )
        qa = Vacante.objects.get(
            proyecto__nombre__startswith="BrainTwist", titulo="QA / Testing"
        )
        self.assertEqual(gymlog.estado, Vacante.ESTADO_CUBIERTA)
        self.assertEqual(qa.estado, Vacante.ESTADO_CUBIERTA)

        correr_seed(self.ahora)

        gymlog.refresh_from_db()
        qa.refresh_from_db()
        self.assertEqual(gymlog.estado, Vacante.ESTADO_CUBIERTA)
        self.assertEqual(qa.estado, Vacante.ESTADO_CUBIERTA)
        self.assertFalse(
            Vacante.objects.filter(
                estado=Vacante.ESTADO_ABIERTA,
                cupos_ocupados__gte=F("cupos_totales"),
            ).exists()
        )

    def test_recorrida_no_reduce_cupos_ni_deja_llena_abierta(self):
        """Vacante legada con cupos_ocupados > fixture (membresías de testers
        con el trigger deshabilitado, caso PetMatch en Neon 4/2): la
        re-corrida no reduce cupos_totales por debajo de lo ocupado (si no,
        chk_cupos_no_exceden abortaría el seed entero) y deja la vacante llena
        como 'cubierta', no como 'abierta'."""
        vac = Vacante.objects.get(
            proyecto__nombre__startswith="PetMatch", titulo="Fullstack Developer"
        )
        Vacante.objects.filter(pk=vac.pk).update(cupos_totales=4, cupos_ocupados=4)

        correr_seed(self.ahora)  # no debe violar chk_cupos_no_exceden

        vac.refresh_from_db()
        self.assertGreaterEqual(vac.cupos_totales, vac.cupos_ocupados)
        self.assertEqual(vac.estado, Vacante.ESTADO_CUBIERTA)

    def test_drift_a_terminal_no_crash_y_normaliza(self):
        """Proyecto seed que cayó en estado terminal (p. ej. reset manual en
        Neon): no se revierte ni se reactiva, y sus vacantes abiertas (incluida
        una fila legada) se normalizan a 'cancelada' sin abortar el seed."""
        petmatch = Proyecto.objects.get(nombre__startswith="PetMatch")
        services_proyectos.cambiar_estado(petmatch, Proyecto.ESTADO_CANCELADO)
        legada = Vacante.objects.create(
            proyecto=petmatch,
            titulo="Legacy Abierta",
            descripcion="Vacante legada que el seed no debe dejar abierta.",
            cupos_totales=1,
            estado=Vacante.ESTADO_ABIERTA,
        )

        correr_seed(self.ahora)  # no debe lanzar TransicionEstadoInvalida

        petmatch.refresh_from_db()
        legada.refresh_from_db()
        self.assertEqual(petmatch.estado, Proyecto.ESTADO_CANCELADO)
        self.assertEqual(legada.estado, Vacante.ESTADO_CANCELADA)
        self.assertFalse(
            Vacante.objects.filter(
                proyecto=petmatch, estado=Vacante.ESTADO_ABIERTA
            ).exists()
        )

    def test_drift_invalido_no_crash_ni_rollback(self):
        """Drift que la matriz no permite revertir al fixture (p. ej.
        en_desarrollo vs fixture 'publicado'): el seed avisa y conserva el
        estado actual sin abortar la corrida completa."""
        brain = Proyecto.objects.get(nombre__startswith="BrainTwist")
        for estado in (
            Proyecto.ESTADO_RECLUTANDO,
            Proyecto.ESTADO_EQUIPO_COMPLETO,
            Proyecto.ESTADO_EN_DESARROLLO,
        ):
            services_proyectos.cambiar_estado(brain, estado)

        correr_seed(self.ahora)  # no debe lanzar ni hacer rollback

        brain.refresh_from_db()
        self.assertEqual(brain.estado, Proyecto.ESTADO_EN_DESARROLLO)
        # El resto del seed sí se aplicó: el borrador sigue intacto.
        self.assertTrue(
            Proyecto.objects.filter(nombre__startswith="DevNotes").exists()
        )