from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Habilidad, Perfil, UsuarioHabilidad
from apps.applications import models as m
from apps.applications import services as s
from apps.applications.models import Postulacion
from apps.applications.services import (
    ConfiguracionPesosNoDisponibleError,
    PostulacionDuplicadaError,
    VacanteNoPostulable,
    crear_postulacion,
)
from apps.matching.models import ConfiguracionPesosMatching
from apps.projects.models import Proyecto, Vacante, VacanteHabilidadRequerida
from apps.projects.tests.helpers import lleva_a
from apps.teams.models import EquipoMembresia

Usuario = get_user_model()

FACTORES = {"habilidades", "nivel", "tecnologias", "experiencia", "disponibilidad"}


class CrearPostulacionTests(TestCase):
    def setUp(self):
        # La tabla de pesos NO viene sembrada en la base de pruebas (los
        # tests de matching asumen que arranca vacía), así que se crea aquí.
        self.pesos = ConfiguracionPesosMatching.objects.create(
            nombre="Ponderación estándar v1.0 (test)",
            peso_habilidades=Decimal("0.350"),
            peso_nivel=Decimal("0.150"),
            peso_tecnologias=Decimal("0.300"),
            peso_experiencia=Decimal("0.100"),
            peso_disponibilidad=Decimal("0.100"),
        )
        creador = Usuario.objects.create_user(
            "creador-svc@devmatch.test", "creador-svc", password="Clave-123!"
        )
        self.postulante = Usuario.objects.create_user(
            "post-svc@devmatch.test", "post-svc", password="Clave-123!"
        )
        proyecto = Proyecto.objects.create(
            creador=creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=proyecto, titulo="Backend", descripcion="desc", cupos_totales=2
        )
        self.habilidad = Habilidad.objects.create(nombre="Python-svc")
        VacanteHabilidadRequerida.objects.create(
            vacante=self.vacante, habilidad=self.habilidad
        )
        self.perfil = Perfil.objects.create(
            usuario=self.postulante,
            nivel="intermedio",
            experiencia_anios=3,
            disponibilidad_horas_semana=20,
        )
        UsuarioHabilidad.objects.create(
            usuario=self.postulante, habilidad=self.habilidad
        )

    def test_crea_postulacion_con_snapshot_completo(self):
        p = crear_postulacion(self.postulante, self.vacante)
        self.assertEqual(p.estado, "pendiente")
        self.assertEqual(p.pesos_usados, self.pesos)
        self.assertEqual(set(p.match_factores), FACTORES)
        self.assertEqual(p.match_factores["habilidades"]["score"], 100.0)
        # 35.0 + 10.0 + 30.0 + 6.0 + 5.0 = 86.0 con los pesos 0.35/0.15/0.30/0.10/0.10
        self.assertAlmostEqual(float(p.match_score), 86.0, places=1)

    def test_snapshot_no_cambia_si_el_perfil_cambia_despues(self):
        """CR-07 / CR-12: el desglose queda congelado al postular."""
        p = crear_postulacion(self.postulante, self.vacante)
        antes = dict(p.match_factores)
        score_antes = p.match_score

        self.perfil.nivel = "avanzado"
        self.perfil.experiencia_anios = 10
        self.perfil.save()

        p.refresh_from_db()
        self.assertEqual(p.match_factores, antes)
        self.assertEqual(p.match_score, score_antes)

    def test_postulacion_activa_duplicada_levanta_error(self):
        crear_postulacion(self.postulante, self.vacante)
        with self.assertRaises(PostulacionDuplicadaError):
            crear_postulacion(self.postulante, self.vacante)
        self.assertEqual(Postulacion.objects.count(), 1)

    def test_puede_volver_a_postular_tras_un_rechazo(self):
        primera = crear_postulacion(self.postulante, self.vacante)
        primera.estado = "rechazada"
        primera.save()

        segunda = crear_postulacion(self.postulante, self.vacante)
        self.assertNotEqual(primera.pk, segunda.pk)
        self.assertEqual(Postulacion.objects.count(), 2)

    def test_usuario_sin_perfil_postula_con_valores_por_defecto(self):
        otro = Usuario.objects.create_user(
            "sin-perfil-crear@devmatch.test", "sin-perfil-crear", password="Clave-123!"
        )
        self.assertFalse(Perfil.objects.filter(usuario=otro).exists())

        p = crear_postulacion(otro, self.vacante)
        # principiante = 1/3 de la escala de nivel
        self.assertAlmostEqual(p.match_factores["nivel"]["score"], 33.33, places=1)

    def test_sin_pesos_activos_levanta_error_claro(self):
        ConfiguracionPesosMatching.objects.update(es_activo=False)
        with self.assertRaises(ConfiguracionPesosNoDisponibleError):
            crear_postulacion(self.postulante, self.vacante)

    def test_vacante_no_abierta_no_admite_postulacion(self):
        self.vacante.estado = Vacante.ESTADO_CUBIERTA
        self.vacante.save()
        with self.assertRaises(VacanteNoPostulable):
            crear_postulacion(self.postulante, self.vacante)
        self.assertEqual(Postulacion.objects.count(), 0)

    def test_proyecto_finalizado_no_admite_postulacion(self):
        lleva_a(self.vacante.proyecto, Proyecto.ESTADO_FINALIZADO)
        # La vacante sigue 'abierta' (cerrarla es tarea del servicio/form de
        # projects): aquí se comprueba que el estado del proyecto por sí solo
        # ya bloquea la postulación.
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.estado, Vacante.ESTADO_ABIERTA)
        with self.assertRaises(VacanteNoPostulable):
            crear_postulacion(self.postulante, self.vacante)
        self.assertEqual(Postulacion.objects.count(), 0)

    def test_proyecto_cancelado_no_admite_postulacion(self):
        self.vacante.proyecto.estado = Proyecto.ESTADO_CANCELADO
        self.vacante.proyecto.cancelado_en = timezone.now()
        self.vacante.proyecto.save()
        with self.assertRaises(VacanteNoPostulable):
            crear_postulacion(self.postulante, self.vacante)
        self.assertEqual(Postulacion.objects.count(), 0)


class AceptarPostulacionBase(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-aceptar2@devmatch.test", "creador-aceptar2", password="Clave-123!"
        )
        self.postulante = Usuario.objects.create_user(
            "postulante-aceptar2@devmatch.test", "postulante-aceptar2", password="Clave-123!"
        )
        Perfil.objects.create(usuario=self.postulante)  # disponibilidad_horas_semana=10 (default)
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )

    def _postular(self, **extra):
        datos = dict(
            vacante=self.vacante,
            postulante=self.postulante,
            match_score=Decimal("80.00"),
            match_factores={"habilidades": 80},
        )
        datos.update(extra)
        return m.Postulacion.objects.create(**datos)


class AceptacionFelizTests(AceptarPostulacionBase):
    def test_aceptar_desde_pendiente_crea_membresia_y_marca_aceptada(self):
        postulacion = self._postular(estado=m.Postulacion.ESTADO_PENDIENTE)

        membresia = s.aceptar_postulacion(postulacion, decidido_por=self.creador)

        postulacion.refresh_from_db()
        self.vacante.refresh_from_db()

        self.assertEqual(postulacion.estado, m.Postulacion.ESTADO_ACEPTADA)
        self.assertEqual(postulacion.decidido_por, self.creador)
        self.assertIsNotNone(postulacion.decidido_en)

        self.assertIsInstance(membresia, EquipoMembresia)
        self.assertEqual(membresia.usuario, self.postulante)
        self.assertEqual(membresia.vacante, self.vacante)
        self.assertEqual(membresia.proyecto, self.proyecto)
        self.assertEqual(membresia.postulacion, postulacion)
        self.assertEqual(membresia.estado, EquipoMembresia.ESTADO_ACTIVO)

        # cupos_ocupados lo escribe el trigger, no el servicio.
        self.assertEqual(self.vacante.cupos_ocupados, 1)


class EstadoPostulacionTests(AceptarPostulacionBase):
    def test_aceptar_desde_preseleccionada_tambien_funciona(self):
        postulacion = self._postular(estado=m.Postulacion.ESTADO_PRESELECCIONADA)

        membresia = s.aceptar_postulacion(postulacion, decidido_por=self.creador)

        postulacion.refresh_from_db()
        self.assertEqual(postulacion.estado, m.Postulacion.ESTADO_ACEPTADA)
        self.assertIsInstance(membresia, EquipoMembresia)

    def test_estados_no_aceptables_lanzan_excepcion_y_no_cambian_nada(self):
        for estado in (
            m.Postulacion.ESTADO_RECHAZADA,
            m.Postulacion.ESTADO_RETIRADA,
            m.Postulacion.ESTADO_ACEPTADA,
        ):
            with self.subTest(estado=estado):
                postulacion = self._postular(estado=estado)

                with self.assertRaises(s.PostulacionNoAceptable):
                    s.aceptar_postulacion(postulacion, decidido_por=self.creador)

                postulacion.refresh_from_db()
                self.assertEqual(postulacion.estado, estado)
                self.assertEqual(
                    EquipoMembresia.objects.filter(postulacion=postulacion).count(), 0
                )


class CapacidadVacanteTests(AceptarPostulacionBase):
    def setUp(self):
        super().setUp()
        self.vacante.cupos_totales = 1
        self.vacante.save()
        self.otro_postulante = Usuario.objects.create_user(
            "otro-aceptar2@devmatch.test", "otro-aceptar2", password="Clave-123!"
        )
        Perfil.objects.create(usuario=self.otro_postulante)

    def _llenar_el_unico_cupo(self):
        primera = self._postular(postulante=self.otro_postulante)
        s.aceptar_postulacion(primera, decidido_por=self.creador)
        # El trigger actualiza la fila en la base, pero self.vacante es el
        # mismo objeto Python desde setUp: FK cachea lo que le pasas
        # directo, así que sin este refresh las siguientes _postular()
        # seguirían viendo cupos_ocupados=0/estado='abierta' en memoria.
        self.vacante.refresh_from_db()

    def test_vacante_llena_lanza_excepcion_y_no_acepta(self):
        self._llenar_el_unico_cupo()
        segunda = self._postular()

        with self.assertRaises(s.VacanteSinCupo):
            s.aceptar_postulacion(segunda, decidido_por=self.creador)

        segunda.refresh_from_db()
        self.assertEqual(segunda.estado, m.Postulacion.ESTADO_PENDIENTE)
        self.assertEqual(
            EquipoMembresia.objects.filter(postulacion=segunda).count(), 0
        )

    def test_insercion_directa_sobre_vacante_llena_choca_con_el_constraint(self):
        # Red de seguridad de la base, no del servicio: confirma que
        # chk_cupos_no_exceden (fix de projects.0005) sigue ahi aunque
        # alguien se salte el servicio por completo.
        self._llenar_el_unico_cupo()
        segunda = self._postular()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EquipoMembresia.objects.create(
                    proyecto=self.proyecto,
                    vacante=self.vacante,
                    usuario=self.postulante,
                    postulacion=segunda,
                )
        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.cupos_ocupados, 1)


class DuplicadoEnElMismoProyectoTests(AceptarPostulacionBase):
    def test_ya_miembro_del_proyecto_por_otra_vacante_no_se_puede_aceptar(self):
        primera = self._postular()
        s.aceptar_postulacion(primera, decidido_por=self.creador)

        otra_vacante = Vacante.objects.create(
            proyecto=self.proyecto, titulo="Frontend", descripcion="desc", cupos_totales=3
        )
        segunda = self._postular(
            vacante=otra_vacante, match_score=Decimal("70.00"), match_factores={"h": 70}
        )

        with self.assertRaises(s.PostulacionNoAceptable):
            s.aceptar_postulacion(segunda, decidido_por=self.creador)

        segunda.refresh_from_db()
        self.assertEqual(segunda.estado, m.Postulacion.ESTADO_PENDIENTE)
        self.assertEqual(
            EquipoMembresia.objects.filter(postulacion=segunda).count(), 0
        )


class CargaDisponibilidadTests(AceptarPostulacionBase):
    def setUp(self):
        super().setUp()
        self.otro_proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Otro", descripcion="desc"
        )
        self.otra_vacante = Vacante.objects.create(
            proyecto=self.otro_proyecto, titulo="Otro rol", descripcion="desc", cupos_totales=3
        )

    def _dar_membresia_previa(self, estado_proyecto):
        """Deja a self.postulante con una membresía activa en self.otro_proyecto."""
        previa = self._postular(
            vacante=self.otra_vacante, match_score=Decimal("60.00"), match_factores={"h": 60}
        )
        s.aceptar_postulacion(previa, decidido_por=self.creador)
        lleva_a(self.otro_proyecto, estado_proyecto)

    def test_carga_incompatible_bloquea_la_aceptacion_y_no_cambia_nada(self):
        # disponibilidad default = 10. 1 membresía previa = 10h de carga.
        # +10h nuevas = 20h > 10h disponibles.
        self._dar_membresia_previa(Proyecto.ESTADO_EN_DESARROLLO)
        nueva = self._postular()

        with self.assertRaises(s.CargaIncompatible):
            s.aceptar_postulacion(nueva, decidido_por=self.creador)

        nueva.refresh_from_db()
        self.assertEqual(nueva.estado, m.Postulacion.ESTADO_PENDIENTE)
        self.assertEqual(
            EquipoMembresia.objects.filter(postulacion=nueva).count(), 0
        )

    def test_limite_exacto_permite_la_aceptacion(self):
        # disponibilidad=20, 1 membresía previa=10h, +10h nuevas=20h == 20h: permitido.
        perfil = Perfil.objects.get(usuario=self.postulante)
        perfil.disponibilidad_horas_semana = 20
        perfil.save()
        self._dar_membresia_previa(Proyecto.ESTADO_EN_DESARROLLO)
        nueva = self._postular()

        membresia = s.aceptar_postulacion(nueva, decidido_por=self.creador)
        self.assertIsInstance(membresia, EquipoMembresia)

    def test_membresias_en_proyectos_finalizados_o_cancelados_no_cuentan(self):
        for estado_final in (Proyecto.ESTADO_FINALIZADO, Proyecto.ESTADO_CANCELADO):
            with self.subTest(estado=estado_final):
                otro_proyecto = Proyecto.objects.create(
                    creador=self.creador, nombre=f"Fin-{estado_final}", descripcion="desc"
                )
                otra_vacante = Vacante.objects.create(
                    proyecto=otro_proyecto, titulo="Rol", descripcion="desc", cupos_totales=3
                )
                postulante = Usuario.objects.create_user(
                    f"postulante-{estado_final}@devmatch.test",
                    f"postulante-{estado_final}",
                    password="Clave-123!",
                )
                Perfil.objects.create(usuario=postulante)  # disponibilidad=10 default

                previa = self._postular(
                    vacante=otra_vacante,
                    postulante=postulante,
                    match_score=Decimal("60.00"),
                    match_factores={"h": 60},
                )
                s.aceptar_postulacion(previa, decidido_por=self.creador)
                lleva_a(otro_proyecto, estado_final)

                # carga_actual debería ser 0 (la membresía anterior no
                # cuenta): +10h nuevas <= 10h disponibles -> permitido.
                nueva = self._postular(postulante=postulante)
                membresia = s.aceptar_postulacion(nueva, decidido_por=self.creador)
                self.assertIsInstance(membresia, EquipoMembresia)


class PerfilFaltanteTests(AceptarPostulacionBase):
    def test_verificar_carga_no_revienta_si_el_usuario_no_tiene_perfil(self):
        # Postulante deliberadamente sin Perfil.objects.create() — a
        # diferencia de self.postulante del setUp.
        sin_perfil = Usuario.objects.create_user(
            "sin-perfil-aceptar@devmatch.test", "sin-perfil-aceptar", password="Clave-123!"
        )
        self.assertFalse(Perfil.objects.filter(usuario=sin_perfil).exists())

        postulacion = self._postular(
            postulante=sin_perfil, match_score=Decimal("65.00"), match_factores={"h": 65}
        )

        # No debe escapar Perfil.DoesNotExist (excepcion de ORM, no de
        # dominio): verificar_carga debe resolverlo, no filtrarlo.
        membresia = s.aceptar_postulacion(postulacion, decidido_por=self.creador)

        self.assertIsInstance(membresia, EquipoMembresia)
        self.assertTrue(Perfil.objects.filter(usuario=sin_perfil).exists())
