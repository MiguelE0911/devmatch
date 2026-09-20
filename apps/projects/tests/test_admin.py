from django.contrib.admin.sites import site
from django.test import TestCase

from apps.projects.models import (
    Proyecto,
    ProyectoMedia,
    Vacante,
    VacanteHabilidadRequerida,
    VacanteTecnologiaRequerida,
)


class ProjectsAdminRegistroTests(TestCase):
    def test_modelos_registrados_en_el_admin(self):
        for modelo in (Proyecto, Vacante, ProyectoMedia):
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(site.is_registered(modelo))

    def test_tablas_puente_no_registradas(self):
        # Mismo motivo que en accounts: Django no permite registrar un
        # modelo con PK compuesta (CompositePrimaryKey) en el admin.
        for modelo in (VacanteHabilidadRequerida, VacanteTecnologiaRequerida):
            with self.subTest(modelo=modelo.__name__):
                self.assertFalse(site.is_registered(modelo))

    def test_cupos_ocupados_es_readonly_en_vacante(self):
        # cupos_ocupados lo mantiene el trigger trg_membresia_actualiza_cupos
        # en la base real; no debe poder editarse a mano desde el admin.
        admin_instance = site._registry[Vacante]
        self.assertIn("cupos_ocupados", admin_instance.readonly_fields)
