from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import CompositePrimaryKey
from django.test import TestCase

from apps.accounts.models import Habilidad, Tecnologia
from apps.projects import models as m

Usuario = get_user_model()


class ProyectoContractTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador@devmatch.test", "creador", password="Clave-123!"
        )

    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(m.Proyecto._meta.db_table, "proyectos")
        columnas = {f.name: f.column for f in m.Proyecto._meta.fields}
        esperadas = {
            "creador": "creador_id",
            "nombre": "nombre",
            "descripcion": "descripcion",
            "estado": "estado",
            "es_activo": "es_activo",
            "logo_url": "logo_url",
            "finalizado_en": "finalizado_en",
            "cancelado_en": "cancelado_en",
            "desactivado_en": "desactivado_en",
            "desactivado_por": "desactivado_por_id",
            "creado_en": "creado_en",
            "actualizado_en": "actualizado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_estados_disponibles_coinciden_con_el_esquema_oficial(self):
        valores = {valor for valor, _ in m.Proyecto.ESTADO_CHOICES}
        self.assertEqual(
            valores,
            {
                "borrador",
                "publicado",
                "reclutando",
                "equipo_completo",
                "en_desarrollo",
                "finalizado",
                "cancelado",
            },
        )

    def test_defaults_coinciden_con_el_esquema(self):
        proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.assertEqual(proyecto.estado, m.Proyecto.ESTADO_BORRADOR)
        self.assertTrue(proyecto.es_activo)

    def test_no_se_puede_borrar_un_creador_con_proyectos(self):
        m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        # DatabaseError y no IntegrityError: el trigger de usuarios aborta con
        # SQLSTATE P0001, que Django no traduce a IntegrityError.
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self.creador.delete()


class VacanteContractTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-vacante@devmatch.test", "creador-vacante", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(m.Vacante._meta.db_table, "vacantes")
        columnas = {f.name: f.column for f in m.Vacante._meta.fields}
        esperadas = {
            "proyecto": "proyecto_id",
            "titulo": "titulo",
            "descripcion": "descripcion",
            "cupos_totales": "cupos_totales",
            "cupos_ocupados": "cupos_ocupados",
            "estado": "estado",
            "es_activo": "es_activo",
            "desactivado_en": "desactivado_en",
            "desactivado_por": "desactivado_por_id",
            "creado_en": "creado_en",
            "actualizado_en": "actualizado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_estados_disponibles_coinciden_con_el_esquema_oficial(self):
        valores = {valor for valor, _ in m.Vacante.ESTADO_CHOICES}
        self.assertEqual(valores, {"abierta", "cubierta", "cancelada"})

    def test_defaults_coinciden_con_el_esquema(self):
        vacante = m.Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )
        self.assertEqual(vacante.estado, m.Vacante.ESTADO_ABIERTA)
        self.assertEqual(vacante.cupos_ocupados, 0)
        self.assertTrue(vacante.es_activo)

    def test_desactivar_un_proyecto_lo_conserva_en_la_base(self):
        m.Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )
        # `trg_bloquear_borrado_proyectos` aborta el DELETE antes del
        # ON DELETE CASCADE de vacantes.proyecto_id: el borrado no es una vía
        # válida y la baja se hace con es_activo=False.
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self.proyecto.delete()
        self.assertEqual(m.Vacante.objects.count(), 1)

        self.proyecto.es_activo = False
        self.proyecto.save()
        self.proyecto.refresh_from_db()
        self.assertFalse(self.proyecto.es_activo)
        self.assertEqual(m.Vacante.objects.count(), 1)


class ProyectoMediaContractTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-media@devmatch.test", "creador-media", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(m.ProyectoMedia._meta.db_table, "proyecto_media")
        columnas = {f.name: f.column for f in m.ProyectoMedia._meta.fields}
        esperadas = {
            "proyecto": "proyecto_id",
            "tipo": "tipo",
            "archivo_url": "archivo_url",
            "orden": "orden",
            "es_activo": "es_activo",
            "creado_en": "creado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)

    def test_no_tiene_actualizado_en_ni_desactivado_por(self):
        # A diferencia de proyectos/vacantes: es un adjunto, no un registro
        # crítico de negocio (ver DevMatch-BD, 5.2).
        nombres = {f.name for f in m.ProyectoMedia._meta.fields}
        self.assertNotIn("actualizado_en", nombres)
        self.assertNotIn("desactivado_por", nombres)
        self.assertNotIn("desactivado_en", nombres)

    def test_tipos_disponibles_coinciden_con_el_esquema_oficial(self):
        valores = {valor for valor, _ in m.ProyectoMedia.TIPO_CHOICES}
        self.assertEqual(valores, {"logo", "prototipo"})

    def test_defaults_coinciden_con_el_esquema(self):
        media = m.ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=m.ProyectoMedia.TIPO_LOGO,
            archivo_url="https://example.com/logo.png",
        )
        self.assertEqual(media.orden, 0)
        self.assertTrue(media.es_activo)

    def test_no_se_puede_borrar_fisicamente_un_proyecto_con_galeria(self):
        m.ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=m.ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/prototipo.png",
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self.proyecto.delete()
        self.assertEqual(m.ProyectoMedia.objects.count(), 1)

    def test_desactivar_un_proyecto_no_borra_su_galeria(self):
        media = m.ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=m.ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/prototipo.png",
        )
        self.proyecto.es_activo = False
        self.proyecto.save()
        media.refresh_from_db()
        self.assertTrue(media.es_activo)


class TablasPuenteRequisitosTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-puente@devmatch.test", "creador-puente", password="Clave-123!"
        )
        self.proyecto = m.Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = m.Vacante.objects.create(
            proyecto=self.proyecto, titulo="Backend", descripcion="desc", cupos_totales=3
        )
        self.habilidad = Habilidad.objects.create(nombre="Backend Development")
        self.tecnologia = Tecnologia.objects.create(nombre="Django")

    def test_uso_pk_compuesta_sin_columna_id(self):
        for modelo in (m.VacanteHabilidadRequerida, m.VacanteTecnologiaRequerida):
            with self.subTest(modelo=modelo.__name__):
                self.assertIsInstance(modelo._meta.pk, CompositePrimaryKey)
                nombres = {f.name for f in modelo._meta.fields}
                self.assertNotIn("id", nombres)

    def test_columnas_puente_mapean_al_esquema(self):
        self.assertEqual(
            m.VacanteHabilidadRequerida._meta.db_table, "vacante_habilidades_requeridas"
        )
        self.assertEqual(
            m.VacanteHabilidadRequerida._meta.get_field("vacante").column, "vacante_id"
        )
        self.assertEqual(
            m.VacanteHabilidadRequerida._meta.get_field("habilidad").column, "habilidad_id"
        )
        self.assertEqual(
            m.VacanteTecnologiaRequerida._meta.db_table, "vacante_tecnologias_requeridas"
        )
        self.assertEqual(
            m.VacanteTecnologiaRequerida._meta.get_field("vacante").column, "vacante_id"
        )
        self.assertEqual(
            m.VacanteTecnologiaRequerida._meta.get_field("tecnologia").column,
            "tecnologia_id",
        )

    def test_no_se_duplica_requisito_de_habilidad(self):
        m.VacanteHabilidadRequerida.objects.create(
            vacante=self.vacante, habilidad=self.habilidad
        )
        with self.assertRaises(IntegrityError):
            m.VacanteHabilidadRequerida.objects.create(
                vacante=self.vacante, habilidad=self.habilidad
            )

    def test_se_persisten_los_requisitos(self):
        m.VacanteHabilidadRequerida.objects.create(
            vacante=self.vacante, habilidad=self.habilidad
        )
        m.VacanteTecnologiaRequerida.objects.create(
            vacante=self.vacante, tecnologia=self.tecnologia
        )
        self.assertEqual(m.VacanteHabilidadRequerida.objects.count(), 1)
        self.assertEqual(m.VacanteTecnologiaRequerida.objects.count(), 1)

    def test_no_se_puede_borrar_fisicamente_una_vacante_con_requisitos(self):
        m.VacanteHabilidadRequerida.objects.create(
            vacante=self.vacante, habilidad=self.habilidad
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self.vacante.delete()
        self.assertEqual(m.VacanteHabilidadRequerida.objects.count(), 1)

    def test_desactivar_una_vacante_no_borra_sus_requisitos(self):
        # vacante_habilidades_requeridas es tabla puente pura: no lleva
        # es_activo, asi que la unica via de baja es desactivar la vacante.
        self.assertFalse(
            hasattr(m.VacanteHabilidadRequerida, "es_activo"),
            "la tabla puente no deberia tener es_activo",
        )
        m.VacanteHabilidadRequerida.objects.create(
            vacante=self.vacante, habilidad=self.habilidad
        )
        self.vacante.es_activo = False
        self.vacante.save()
        self.vacante.refresh_from_db()
        self.assertFalse(self.vacante.es_activo)
        self.assertEqual(m.VacanteHabilidadRequerida.objects.count(), 1)
