from django.contrib.admin.sites import site
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.admin import UsuarioAdmin, UsuarioCreationForm
from apps.accounts.models import (
    Habilidad,
    Interes,
    Perfil,
    Tecnologia,
    Usuario,
    UsuarioHabilidad,
    UsuarioInteres,
    UsuarioTecnologia,
)


class UsuarioAdminRegistroTests(TestCase):
    def test_modelos_registrados_en_el_admin(self):
        for modelo in (Usuario, Perfil, Habilidad, Tecnologia, Interes):
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(site.is_registered(modelo))

    def test_tablas_puente_no_registradas(self):
        for modelo in (UsuarioHabilidad, UsuarioTecnologia, UsuarioInteres):
            with self.subTest(modelo=modelo.__name__):
                self.assertFalse(site.is_registered(modelo))

    def test_add_form_es_usuariocreationform(self):
        admin = UsuarioAdmin(Usuario, site)
        self.assertEqual(admin.add_form, UsuarioCreationForm)


class UsuarioCreationFormTests(TestCase):
    def _datos_validos(self, **overrides):
        datos = {
            "email": "form@devmatch.test",
            "username": "form",
            "first_name": "Form",
            "last_name": "User",
            "password1": "ClaveFuerte-123!",
            "password2": "ClaveFuerte-123!",
        }
        datos.update(overrides)
        return datos

    def test_rechaza_contrasenas_distintas(self):
        form = UsuarioCreationForm(data=self._datos_validos(password2="Otra-123!"))
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_guarda_usuario_con_password_hasheado(self):
        form = UsuarioCreationForm(data=self._datos_validos())
        self.assertTrue(form.is_valid())
        usuario = form.save()
        self.assertNotEqual(usuario.password, "ClaveFuerte-123!")
        self.assertTrue(usuario.check_password("ClaveFuerte-123!"))
        self.assertFalse(usuario.es_admin)


class UsuarioAdminPaginasTests(TestCase):
    def setUp(self):
        self.supervisor = Usuario.objects.create_superuser(
            "admin@devmatch.test", "admin", password="Clave-123!"
        )
        self.client.force_login(self.supervisor)

    def _add_url(self):
        return reverse("admin:accounts_usuario_add")

    def test_pagina_de_alta_responde_200(self):
        response = self.client.get(self._add_url())
        self.assertEqual(response.status_code, 200)

    def test_crear_usuario_desde_pagina_de_alta(self):
        response = self.client.post(
            self._add_url(),
            {
                "email": "nuevo@devmatch.test",
                "username": "nuevo",
                "first_name": "Nuevo",
                "last_name": "User",
                "password1": "ClaveFuerte-123!",
                "password2": "ClaveFuerte-123!",
            },
        )
        self.assertRedirects(response, reverse("admin:accounts_usuario_changelist"))
        usuario = Usuario.objects.get(email="nuevo@devmatch.test")
        self.assertTrue(usuario.check_password("ClaveFuerte-123!"))

    def test_editar_usuario_no_expone_password_editable(self):
        admin = UsuarioAdmin(Usuario, site)
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        readonly = admin.get_readonly_fields(request, obj=self.supervisor)
        self.assertIn("password", readonly)

    def test_admin_requiere_is_staff_derivado_de_es_admin(self):
        no_admin = Usuario.objects.create_user(
            "tramite@devmatch.test", "tramite", password="Clave-123!"
        )
        self.client.force_login(no_admin)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse("admin:index"))