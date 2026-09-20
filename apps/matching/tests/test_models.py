from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.matching import models as m


def pesos_validos():
    return {
        "nombre": "Perfil por defecto",
        "peso_habilidades": Decimal("0.400"),
        "peso_nivel": Decimal("0.200"),
        "peso_tecnologias": Decimal("0.200"),
        "peso_experiencia": Decimal("0.100"),
        "peso_disponibilidad": Decimal("0.100"),
    }


class ConfiguracionPesosMatchingContractTests(TestCase):
    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(m.ConfiguracionPesosMatching._meta.db_table, "configuracion_pesos_matching")
        columnas = {f.name: f.column for f in m.ConfiguracionPesosMatching._meta.fields}
        esperadas = {
            "nombre": "nombre",
            "peso_habilidades": "peso_habilidades",
            "peso_nivel": "peso_nivel",
            "peso_tecnologias": "peso_tecnologias",
            "peso_experiencia": "peso_experiencia",
            "peso_disponibilidad": "peso_disponibilidad",
            "vigente_desde": "vigente_desde",
            "vigente_hasta": "vigente_hasta",
            "es_activo": "es_activo",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_campos_de_peso_son_decimales_4_3(self):
        for campo in (
            "peso_habilidades",
            "peso_nivel",
            "peso_tecnologias",
            "peso_experiencia",
            "peso_disponibilidad",
        ):
            field = m.ConfiguracionPesosMatching._meta.get_field(campo)
            self.assertEqual(field.max_digits, 4, campo)
            self.assertEqual(field.decimal_places, 3, campo)

    def test_defaults_coinciden_con_el_esquema(self):
        config = m.ConfiguracionPesosMatching.objects.create(**pesos_validos())
        self.assertTrue(config.es_activo)
        self.assertIsNotNone(config.vigente_desde)
        self.assertIsNone(config.vigente_hasta)


class ConfiguracionPesosMatchingValidationTests(TestCase):
    def test_los_cinco_pesos_deben_sumar_exactamente_1_000(self):
        datos = pesos_validos()
        datos["peso_nivel"] = Decimal("0.300")
        config = m.ConfiguracionPesosMatching(**datos)
        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_pesos_validos_suman_1_000(self):
        config = m.ConfiguracionPesosMatching(**pesos_validos())
        config.full_clean()

    def test_solo_un_registro_activo_a_la_vez(self):
        m.ConfiguracionPesosMatching.objects.create(**pesos_validos())
        segundo = pesos_validos()
        segundo["nombre"] = "Perfil alterno"
        with self.assertRaises(IntegrityError):
            m.ConfiguracionPesosMatching.objects.create(**segundo)

    def test_se_puede_desactivar_el_activo_y_crear_otro(self):
        primero = m.ConfiguracionPesosMatching.objects.create(**pesos_validos())
        primero.es_activo = False
        primero.save()
        segundo = pesos_validos()
        segundo["nombre"] = "Perfil alterno"
        m.ConfiguracionPesosMatching.objects.create(**segundo)
        self.assertEqual(
            m.ConfiguracionPesosMatching.objects.filter(es_activo=True).count(), 1
        )