"""Detecta divergencia entre docs/devmatch_schema_v1.sql y lo que realmente
instala apps/core/migrations/0001_triggers_postgres.py.

Complementa a los tests de modelos: aquellos comprueban el *comportamiento*
mediante la base de datos de pruebas; estos comprueban que el .sql documentado
y la migración digan exactamente lo mismo. Si alguien edita uno y no el otro,
estos tests fallan.

Solo es la mitad de la defensa: la otra mitad es la migración, que es la que
realmente instala los triggers en cualquier base (Neon incluida). Modificar el
.sql sin actualizar la migración no cambia el comportamiento, pero deja el
documento mintiendo, que es justo lo que estos tests detectan.
"""

import re
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.test import TestCase
from unittest import SkipTest

ESQUEMA = Path(settings.BASE_DIR) / "docs" / "devmatch_schema_v1.sql"

RE_FUNCION = re.compile(
    r"CREATE OR REPLACE FUNCTION\s+(\w+)\(\).*?AS \$\$(.*?)\$\$ LANGUAGE plpgsql;",
    re.DOTALL,
)
RE_TRIGGER = re.compile(
    r"CREATE TRIGGER\s+(\w+)\s+(.*?)\s+ON\s+(\w+)(.*?)EXECUTE FUNCTION\s+(\w+)\(\)",
    re.DOTALL,
)


def normaliza(texto):
    """Colapsa espacios para comparar Bodies sin depender del indentado."""
    return re.sub(r"\s+", " ", texto).strip()


def cuerpo_de_pg_get_functiondef(definicion):
    """Extrae el cuerpo plpgsql de la salida de pg_get_functiondef.

    PostgreSQL reetiqueta el delimitador dollar-quoting de `$$` a `$function$`,
    así que el patrón tiene que tolerar cualquier etiqueta.
    """
    coincidencia = re.search(r"AS \$\w*\$(.*?)\$\w*\$", definicion, re.DOTALL)
    return coincidencia.group(1) if coincidencia else definicion


class TriggersCoincidenConElEsquemaTests(TestCase):
    """Compara el catálogo de PostgreSQL contra el .sql oficial."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor != "postgresql":
            raise SkipTest(
                "Requiere PostgreSQL: los triggers y funciones solo existen en Postgres."
            )
        cls.sql = ESQUEMA.read_text(encoding="utf-8")
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT t.tgname,
                       c.relname,
                       p.proname,
                       pg_get_triggerdef(t.oid)
                FROM pg_trigger t
                JOIN pg_class c ON c.oid = t.tgrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_proc p ON p.oid = t.tgfoid
                WHERE NOT t.tgisinternal AND n.nspname = 'public'
                """
            )
            cls.triggers = cursor.fetchall()
            cursor.execute(
                """
                SELECT p.proname, pg_get_functiondef(p.oid), p.prosecdef
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public'
                """
            )
            cls.funciones = cursor.fetchall()

    # ---------------------------------------------------------------- triggers

    def test_el_esquema_declara_19_triggers(self):
        declarados = RE_TRIGGER.findall(self.sql)
        self.assertEqual(
            len(declarados),
            19,
            "Si cambia el conteo, actualiza tambien la docstring de la migracion "
            "0001_triggers_postgres.py y DEVMATCH-BD.md.",
        )

    def test_no_hay_triggers_en_la_base_que_el_esquema_no_declara(self):
        declarados = {t[0] for t in RE_TRIGGER.findall(self.sql)}
        reales = {t[0] for t in self.triggers}
        self.assertEqual(
            reales - declarados,
            set(),
            "Triggers instalados que no estan en devmatch_schema_v1.sql",
        )

    def test_todo_trigger_del_esquema_esta_instalado(self):
        declarados = {t[0] for t in RE_TRIGGER.findall(self.sql)}
        reales = {t[0] for t in self.triggers}
        self.assertEqual(declarados - reales, set(), "Triggers del .sql sin instalar")

    def test_tabla_y_funcion_de_cada_trigger_coinciden(self):
        declarados = {
            nombre: (tabla, funcion) for nombre, _, tabla, _, funcion in RE_TRIGGER.findall(self.sql)
        }
        reales = {t[0]: (t[1], t[2]) for t in self.triggers}
        for nombre, esperado in declarados.items():
            with self.subTest(trigger=nombre):
                self.assertEqual(reales.get(nombre), esperado)

    def test_el_evento_de_cada_trigger_coincide(self):
        for nombre, antes_de_on, tabla, despues_de_on, _ in RE_TRIGGER.findall(self.sql):
            eventos_sql = normaliza(antes_de_on)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t "
                    "JOIN pg_class c ON c.oid = t.tgrelid "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE NOT t.tgisinternal AND n.nspname = 'public' "
                    "AND t.tgname = %s",
                    [nombre],
                )
                definicion = normaliza(cursor.fetchone()[0])
            for evento in ("BEFORE", "AFTER", "UPDATE", "INSERT", "DELETE"):
                with self.subTest(trigger=nombre, evento=evento):
                    self.assertEqual(
                        evento in eventos_sql,
                        evento in definicion,
                        f"{nombre}: la definicion real difiere en '{evento}'",
                    )

    def test_el_bloqueo_de_borrado_cubre_las_10_tablas_de_historial(self):
        esperadas = {
            "usuarios",
            "perfiles",
            "proyectos",
            "proyecto_media",
            "vacantes",
            "postulaciones",
            "invitaciones",
            "equipos_membresias",
            "resenas",
            "reportes",
        }
        bloqueantes = {
            t[1] for t in self.triggers if t[2] == "fn_prevenir_borrado_fisico"
        }
        self.assertEqual(bloqueantes, esperadas)

    def test_los_catalogos_no_estan_bloqueados(self):
        """Los catálogos sí se pueden borrar: es una decisión de diseño."""
        for catalogo in ("habilidades", "tecnologias", "intereses"):
            with self.subTest(catalogo=catalogo):
                self.assertNotIn(
                    catalogo,
                    {t[1] for t in self.triggers if t[2] == "fn_prevenir_borrado_fisico"},
                )

    def test_auditoria_logs_bloquea_update_y_delete(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t "
                "JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE t.tgname = 'trg_inmutable_auditoria'"
            )
            definicion = normaliza(cursor.fetchone()[0])
        self.assertIn("UPDATE", definicion)
        self.assertIn("DELETE", definicion)

    # --------------------------------------------------------------- funciones

    def test_el_esquema_declara_6_funciones(self):
        self.assertEqual(len(RE_FUNCION.findall(self.sql)), 6)

    def test_no_hay_funciones_fn_en_la_base_que_el_esquema_no_declara(self):
        declaradas = {f[0] for f in RE_FUNCION.findall(self.sql)}
        reales = {f[0] for f in self.funciones if f[0].startswith("fn_")}
        self.assertEqual(reales - declaradas, set())

    def test_el_cuerpo_de_cada_funcion_coincide_con_el_esquema(self):
        declaradas = {
            nombre: normaliza(cuerpo) for nombre, cuerpo in RE_FUNCION.findall(self.sql)
        }
        reales = {
            nombre: normaliza(cuerpo_de_pg_get_functiondef(definicion))
            for nombre, definicion, _ in self.funciones
            if nombre in declaradas
        }
        self.assertEqual(set(reales), set(declaradas))
        for nombre, esperado in declaradas.items():
            with self.subTest(funcion=nombre):
                self.assertEqual(
                    reales.get(nombre),
                    esperado,
                    f"El cuerpo de {nombre} difiere entre el .sql y la base de datos",
                )

    def test_ninguna_funcion_usa_security_definer(self):
        """Invariante de seguridad: sin SECURITY DEFINER no hay escalada de
        privilegios ni superficie de inyección en search_path. Si alguna vez se
        necesita, debe fijar SET search_path = pg_catalog, public."""
        inseguras = [nombre for nombre, _, secdef in self.funciones if secdef]
        self.assertEqual(
            inseguras,
            [],
            "Funcion con SECURITY DEFINER sin search_path fijado: superficie de escalada",
        )