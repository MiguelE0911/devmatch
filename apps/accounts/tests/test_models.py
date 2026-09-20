from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import CompositePrimaryKey
from django.test import TestCase

from apps.accounts import models as m

Usuario = get_user_model()


class UsuarioContractTests(TestCase):
    def test_auth_user_model_es_accounts_usuario(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.Usuario")
        self.assertEqual(Usuario._meta.label, "accounts.Usuario")

    def test_tabla_y_columnas_coinciden_con_el_esquema_oficial(self):
        self.assertEqual(Usuario._meta.db_table, "usuarios")
        columnas = {f.name: f.column for f in Usuario._meta.fields}
        esperadas = {
            "email": "email",
            "username": "username",
            "password": "password_hash",
            "last_login": "ultimo_login",
            "first_name": "first_name",
            "last_name": "last_name",
            "es_admin": "es_admin",
            "es_activo": "es_activo",
            "esta_bloqueado": "esta_bloqueado",
            "motivo_bloqueo": "motivo_bloqueo",
            "bloqueado_en": "bloqueado_en",
            "bloqueado_por": "bloqueado_por_id",
            "desactivado_en": "desactivado_en",
            "desactivado_por": "desactivado_por_id",
            "creado_en": "creado_en",
            "actualizado_en": "actualizado_en",
        }
        for campo, columna in esperadas.items():
            self.assertEqual(columnas.get(campo), columna, campo)


class UsuarioManagerTests(TestCase):
    def test_create_user_requiere_email_y_username(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(email=None, username="sin-email")
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(email="sin-username@devmatch.test", username=None)

    def test_create_user_hashea_password_y_no_es_admin(self):
        usuario = Usuario.objects.create_user(
            "basico@devmatch.test", "basico", password="Clave-123!"
        )
        self.assertNotEqual(usuario.password, "Clave-123!")
        self.assertTrue(usuario.password.startswith("pbkdf2"))
        self.assertTrue(usuario.check_password("Clave-123!"))
        self.assertFalse(usuario.es_admin)

    def test_create_superuser_marca_es_admin(self):
        superuser = Usuario.objects.create_superuser(
            "super@devmatch.test", "super", password="Clave-123!"
        )
        self.assertTrue(superuser.es_admin)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)


class UsuarioFlagsTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "flags@devmatch.test", "flags", password="Clave-123!"
        )

    def test_is_staff_e_is_superuser_se_derivan_de_es_admin(self):
        self.assertFalse(self.usuario.is_staff)
        self.assertFalse(self.usuario.is_superuser)
        self.usuario.es_admin = True
        self.usuario.save()
        self.assertTrue(self.usuario.is_staff)
        self.assertTrue(self.usuario.is_superuser)

    def test_is_active_refleja_es_activo_y_esta_bloqueado(self):
        self.assertTrue(self.usuario.is_active)
        self.usuario.esta_bloqueado = True
        self.usuario.save()
        self.assertFalse(self.usuario.is_active)
        self.usuario.esta_bloqueado = False
        self.usuario.es_activo = False
        self.usuario.save()
        self.assertFalse(self.usuario.is_active)


class PerfilTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "perfil@devmatch.test", "perfil", password="Clave-123!"
        )

    def test_contrato_de_tabla_y_columna(self):
        self.assertEqual(m.Perfil._meta.db_table, "perfiles")
        self.assertEqual(m.Perfil._meta.get_field("usuario").column, "usuario_id")

    def test_defaults_coinciden_con_el_esquema(self):
        perfil = m.Perfil.objects.create(usuario=self.usuario)
        self.assertEqual(perfil.nivel, m.Perfil.NIVEL_PRINCIPIANTE)
        self.assertEqual(perfil.experiencia_anios, 0)
        self.assertEqual(perfil.disponibilidad_horas_semana, 10)

    def test_un_solo_perfil_por_usuario(self):
        m.Perfil.objects.create(usuario=self.usuario)
        with self.assertRaises(IntegrityError):
            m.Perfil.objects.create(usuario=self.usuario)


class CatalogoTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            "catalogo@devmatch.test", "catalogo", password="Clave-123!"
        )

    def test_tablas_y_campos_de_cada_catalogo(self):
        habilidad = m.Habilidad.objects.create(
            nombre="Python", categoria="Backend", desactivado_por=self.admin
        )
        tecnologia = m.Tecnologia.objects.create(
            nombre="Postgres", categoria="BD", desactivado_por=self.admin
        )
        interes = m.Interes.objects.create(nombre="Inteligencia Artificial")
        self.assertEqual(habilidad._meta.db_table, "habilidades")
        self.assertEqual(tecnologia._meta.db_table, "tecnologias")
        self.assertEqual(interes._meta.db_table, "intereses")
        self.assertTrue(habilidad.es_activo)
        self.assertIsNotNone(habilidad.creado_en)

    def test_interes_no_tiene_columna_categoria(self):
        campos = {f.name for f in m.Interes._meta.fields}
        self.assertNotIn("categoria", campos)

    def test_nombre_unico_por_catalogo(self):
        m.Habilidad.objects.create(nombre="Django")
        with self.assertRaises(IntegrityError):
            m.Habilidad.objects.create(nombre="Django")


class TablasPuenteTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "puente@devmatch.test", "puente", password="Clave-123!"
        )
        self.habilidad = m.Habilidad.objects.create(nombre="Python")
        self.tecnologia = m.Tecnologia.objects.create(nombre="Django")
        self.interes = m.Interes.objects.create(nombre="IA")

    def test_uso_pk_compuesta_sin_columna_id(self):
        for modelo in (m.UsuarioHabilidad, m.UsuarioTecnologia, m.UsuarioInteres):
            with self.subTest(modelo=modelo.__name__):
                self.assertIsInstance(modelo._meta.pk, CompositePrimaryKey)
                nombres = {f.name for f in modelo._meta.fields}
                self.assertNotIn("id", nombres)

    def test_columnas_puente_mapean_al_esquema(self):
        self.assertEqual(
            m.UsuarioHabilidad._meta.get_field("usuario").column, "usuario_id"
        )
        self.assertEqual(
            m.UsuarioHabilidad._meta.get_field("habilidad").column, "habilidad_id"
        )

    def test_no_se_duplica_asociacion_usuario_habilidad(self):
        m.UsuarioHabilidad.objects.create(usuario=self.usuario, habilidad=self.habilidad)
        with self.assertRaises(IntegrityError):
            m.UsuarioHabilidad.objects.create(usuario=self.usuario, habilidad=self.habilidad)

    def test_se_persisten_las_tres_asociaciones(self):
        m.UsuarioHabilidad.objects.create(usuario=self.usuario, habilidad=self.habilidad)
        m.UsuarioTecnologia.objects.create(usuario=self.usuario, tecnologia=self.tecnologia)
        m.UsuarioInteres.objects.create(usuario=self.usuario, interes=self.interes)
        self.assertEqual(m.UsuarioHabilidad.objects.count(), 1)
        self.assertEqual(m.UsuarioTecnologia.objects.count(), 1)
        self.assertEqual(m.UsuarioInteres.objects.count(), 1)