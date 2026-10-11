from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Habilidad, Perfil, UsuarioHabilidad
from apps.applications.models import Postulacion
from apps.applications.services import (
    ConfiguracionPesosNoDisponibleError,
    PostulacionDuplicadaError,
    crear_postulacion,
)
from apps.matching.models import ConfiguracionPesosMatching
from apps.projects.models import Proyecto, Vacante, VacanteHabilidadRequerida

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
            "sin-perfil@devmatch.test", "sin-perfil", password="Clave-123!"
        )
        self.assertFalse(Perfil.objects.filter(usuario=otro).exists())

        p = crear_postulacion(otro, self.vacante)
        # principiante = 1/3 de la escala de nivel
        self.assertAlmostEqual(p.match_factores["nivel"]["score"], 33.33, places=1)

    def test_sin_pesos_activos_levanta_error_claro(self):
        ConfiguracionPesosMatching.objects.update(es_activo=False)
        with self.assertRaises(ConfiguracionPesosNoDisponibleError):
            crear_postulacion(self.postulante, self.vacante)