"""
Prueba de carrera real para aceptar_postulacion (CR-08).

Usa TransactionTestCase (no TestCase): con TestCase todo el test corre
dentro de una única transacción compartida, lo que hace la concurrencia
real imposible de ejercitar. TransactionTestCase sí confirma cada
operación a la base, permitiendo que dos hilos con conexiones separadas
compitan de verdad por el mismo lock de fila.
"""

import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TransactionTestCase

from apps.accounts.models import Perfil
from apps.applications import models as m
from apps.applications import services as s
from apps.projects.models import Proyecto, Vacante
from apps.teams.models import EquipoMembresia

Usuario = get_user_model()


class AceptarPostulacionConcurrenciaTests(TransactionTestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-concurrencia@devmatch.test", "creador-concurrencia", password="Clave-123!"
        )
        self.postulante_a = Usuario.objects.create_user(
            "postulante-a@devmatch.test", "postulante-a", password="Clave-123!"
        )
        self.postulante_b = Usuario.objects.create_user(
            "postulante-b@devmatch.test", "postulante-b", password="Clave-123!"
        )
        Perfil.objects.create(usuario=self.postulante_a)
        Perfil.objects.create(usuario=self.postulante_b)

        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=1
        )
        self.postulacion_a = m.Postulacion.objects.create(
            vacante=self.vacante,
            postulante=self.postulante_a,
            match_score=Decimal("80.00"),
            match_factores={"h": 80},
        )
        self.postulacion_b = m.Postulacion.objects.create(
            vacante=self.vacante,
            postulante=self.postulante_b,
            match_score=Decimal("75.00"),
            match_factores={"h": 75},
        )

    def test_dos_aceptaciones_simultaneas_en_vacante_de_un_cupo(self):
        barrera = threading.Barrier(2)
        resultados = {}

        def _aceptar(nombre, postulacion_id):
            barrera.wait()  # fuerza a que los dos hilos lleguen juntos
            try:
                postulacion = m.Postulacion.objects.get(pk=postulacion_id)
                s.aceptar_postulacion(postulacion, decidido_por=self.creador)
                resultados[nombre] = "ok"
            except s.VacanteSinCupo:
                resultados[nombre] = "bloqueado_limpio"
            except Exception as exc:  # noqa: BLE001 — queremos ver cualquier otra cosa en el assert
                resultados[nombre] = f"error_inesperado:{type(exc).__name__}"
            finally:
                connections.close_all()

        hilo_a = threading.Thread(
            target=_aceptar, args=("a", self.postulacion_a.pk)
        )
        hilo_b = threading.Thread(
            target=_aceptar, args=("b", self.postulacion_b.pk)
        )
        hilo_a.start()
        hilo_b.start()
        hilo_a.join()
        hilo_b.join()

        # Invariante de negocio: exactamente uno gana, el otro se
        # bloquea limpio con VacanteSinCupo — no un error crudo de Postgres.
        self.assertEqual(sorted(resultados.values()), ["bloqueado_limpio", "ok"])

        self.vacante.refresh_from_db()
        self.assertEqual(self.vacante.cupos_ocupados, 1)
        self.assertEqual(self.vacante.estado, Vacante.ESTADO_CUBIERTA)
        self.assertEqual(
            EquipoMembresia.objects.filter(
                vacante=self.vacante, estado=EquipoMembresia.ESTADO_ACTIVO
            ).count(),
            1,
        )
        self.assertEqual(
            m.Postulacion.objects.filter(estado=m.Postulacion.ESTADO_ACEPTADA).count(),
            1,
        )
        self.assertEqual(
            m.Postulacion.objects.filter(estado=m.Postulacion.ESTADO_PENDIENTE).count(),
            1,
        )
