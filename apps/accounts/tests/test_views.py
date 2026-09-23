from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    Habilidad,
    Interes,
    Perfil,
    Tecnologia,
    UsuarioHabilidad,
    UsuarioInteres,
    UsuarioTecnologia,
)

Usuario = get_user_model()

VALID = {
    "username": "nueva_dev",
    "email": "nueva@devmatch.test",
    "first_name": "Ana",
    "last_name": "Ríos",
    "password1": "Clave-Segura-99!",
    "password2": "Clave-Segura-99!",
}


def valid_data(**overrides):
    data = dict(VALID)
    data.update(overrides)
    return data


class LoginViewTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "login@devmatch.test", "login_user", password="Clave-Segura-99!"
        )

    def test_get_login(self):
        resp = self.client.get(reverse("accounts:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/login.html")
        self.assertContains(resp, "Iniciar sesión")
        self.assertContains(resp, "Correo electrónico o usuario")
        self.assertContains(resp, "data-toggle-password")

    def test_login_correcto_redirige_al_home(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "login@devmatch.test", "password": "Clave-Segura-99!"},
        )
        self.assertRedirects(resp, reverse("core:feed"))

    def test_login_por_username_redirige_al_home(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "login_user", "password": "Clave-Segura-99!"},
        )
        self.assertRedirects(resp, reverse("core:feed"))

    def test_login_por_username_insensible_a_mayusculas(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "  LOGIN_User ", "password": "Clave-Segura-99!"},
        )
        self.assertRedirects(resp, reverse("core:feed"))
        self.assertTrue(resp.wsgi_request.user.is_authenticated)

    def test_login_incorrecto_no_redirige(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "login@devmatch.test", "password": "clave-mala"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Correo electrónico o contraseña incorrectos.")
        self.assertFalse(resp.wsgi_request.user.is_authenticated)

    def test_cuenta_bloqueada_no_entra(self):
        self.usuario.esta_bloqueado = True
        self.usuario.save(update_fields=["esta_bloqueado"])
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "login@devmatch.test", "password": "Clave-Segura-99!"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Correo electrónico o contraseña incorrectos.")


class RegistroViewTests(TestCase):
    def test_get_registro(self):
        resp = self.client.get(reverse("accounts:register"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/register.html")
        self.assertContains(resp, "Regístrate para continuar")
        self.assertContains(resp, "Máximo 30 caracteres")
        self.assertContains(resp, "Mínimo 8 caracteres")
        self.assertEqual(resp.content.decode().count("data-target="), 2)

    def test_registro_valido_crea_usuario_y_redirige_a_login(self):
        resp = self.client.post(reverse("accounts:register"), valid_data())
        self.assertRedirects(resp, reverse("accounts:login"))
        self.assertTrue(Usuario.objects.filter(email="nueva@devmatch.test").exists())

        usuario = Usuario.objects.get(email="nueva@devmatch.test")
        self.assertFalse(usuario.es_admin)
        self.assertEqual(usuario.first_name, "Ana")
        self.assertEqual(usuario.last_name, "Ríos")
        self.assertTrue(usuario.check_password("Clave-Segura-99!"))

    def test_registro_valido_muestra_mensaje_de_exito(self):
        resp = self.client.post(reverse("accounts:register"), valid_data(), follow=True)
        self.assertContains(resp, "¡Cuenta creada!")

    def test_registro_con_campos_vacios_no_crea_usuario(self):
        resp = self.client.post(reverse("accounts:register"), {})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Usuario.objects.count(), 0)

    def test_registro_con_password_distinta_no_crea_usuario(self):
        resp = self.client.post(
            reverse("accounts:register"), valid_data(password2="Otra-Clave-99!")
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Usuario.objects.count(), 0)

    def test_registro_crea_un_solo_usuario_aun_con_datos_repetidos(self):
        self.client.post(reverse("accounts:register"), valid_data())
        resp = self.client.post(reverse("accounts:register"), valid_data())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Usuario.objects.filter(email__iexact="nueva@devmatch.test").count(), 1)


class ProfileDetailViewTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "perfil@devmatch.test", "perfil_user", password="Clave-Segura-99!"
        )
        self.url = reverse("accounts:profile")

    def test_sin_login_redirige_al_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, f"{reverse('accounts:login')}?next={self.url}")

    def test_get_muestra_perfil_autenticado(self):
        self.client.force_login(self.usuario)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/profile_detail.html")
        self.assertContains(resp, "perfil_user")
        self.assertTrue(Perfil.objects.filter(usuario=self.usuario).exists())

    def test_get_crea_perfil_si_no_existe(self):
        self.client.force_login(self.usuario)
        self.client.get(self.url)
        self.assertEqual(Perfil.objects.filter(usuario=self.usuario).count(), 1)

    def test_get_usa_el_template_vista_a(self):
        self.client.force_login(self.usuario)
        resp = self.client.get(self.url)
        self.assertContains(resp, "Editar perfil")


class ProfileEditViewTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "editar@devmatch.test", "editar_user", password="Clave-Segura-99!"
        )
        self.url = reverse("accounts:profile_edit")
        self.perfil = Perfil.objects.create(usuario=self.usuario)

    def test_sin_login_redirige_al_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, f"{reverse('accounts:login')}?next={self.url}")

    def test_get_usa_el_template_vista_b(self):
        self.client.force_login(self.usuario)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/profile_form.html")
        self.assertContains(resp, "Datos personales")
        self.assertContains(resp, "Guardar perfil")

    def test_get_no_crea_duplicado_de_perfil(self):
        self.client.force_login(self.usuario)
        self.client.get(self.url)
        self.assertEqual(Perfil.objects.filter(usuario=self.usuario).count(), 1)

    def test_get_popula_datos_del_usuario(self):
        self.usuario.first_name = "María"
        self.usuario.last_name = "López"
        self.usuario.save()
        self.client.force_login(self.usuario)
        resp = self.client.get(self.url)
        self.assertContains(resp, "María")
        self.assertContains(resp, "López")
        self.assertContains(resp, "editar@devmatch.test")

    def test_post_guarda_datos_y_sincroniza_puentes(self):
        back = Habilidad.objects.create(nombre="Backend")
        ui = Habilidad.objects.create(nombre="UI/UX")
        python = Tecnologia.objects.create(nombre="Python")
        gaming = Interes.objects.create(nombre="Gaming")

        self.client.force_login(self.usuario)
        resp = self.client.post(
            self.url,
            {
                "username": "editar_user",
                "first_name": "Carlos",
                "last_name": "Gómez",
                "email": "editar@devmatch.test",
                "nivel": "intermedio",
                "experiencia_anios": 4,
                "disponibilidad_horas_semana": 20,
                "bio": "Fullstack en formación.",
                "habilidades": [back.pk],
                "tecnologias": [python.pk],
                "intereses": [gaming.pk],
            },
        )
        self.assertRedirects(resp, reverse("accounts:profile"))

        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.nivel, "intermedio")
        self.assertEqual(self.perfil.experiencia_anios, 4)
        self.assertEqual(self.perfil.disponibilidad_horas_semana, 20)
        self.assertEqual(self.perfil.bio, "Fullstack en formación.")

        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, "Carlos")
        self.assertEqual(self.usuario.last_name, "Gómez")
        self.assertEqual(self.usuario.email, "editar@devmatch.test")

        self.assertTrue(
            UsuarioHabilidad.objects.filter(
                usuario=self.usuario, habilidad=back
            ).exists()
        )
        self.assertFalse(
            UsuarioHabilidad.objects.filter(
                usuario=self.usuario, habilidad=ui
            ).exists()
        )
        self.assertTrue(
            UsuarioTecnologia.objects.filter(
                usuario=self.usuario, tecnologia=python
            ).exists()
        )
        self.assertTrue(
            UsuarioInteres.objects.filter(
                usuario=self.usuario, interes=gaming
            ).exists()
        )

    def test_post_elimina_puentes_deseleccionados(self):
        python = Tecnologia.objects.create(nombre="Python")
        UsuarioTecnologia.objects.create(usuario=self.usuario, tecnologia=python)

        self.client.force_login(self.usuario)
        resp = self.client.post(
            self.url,
            {
                "username": "editar_user",
                "first_name": "",
                "last_name": "",
                "email": "editar@devmatch.test",
                "nivel": "principiante",
                "experiencia_anios": 0,
                "disponibilidad_horas_semana": 10,
                "bio": "",
            },
        )
        self.assertRedirects(resp, reverse("accounts:profile"))
        self.assertFalse(
            UsuarioTecnologia.objects.filter(
                usuario=self.usuario, tecnologia=python
            ).exists()
        )

    def test_post_con_username_repetido_no_guarda(self):
        Usuario.objects.create_user("otro@devmatch.test", "tomado", password="Clave-Segura-99!")
        self.client.force_login(self.usuario)
        resp = self.client.post(
            self.url,
            {
                "username": "tomado",
                "first_name": "",
                "last_name": "",
                "email": "editar@devmatch.test",
                "nivel": "principiante",
                "experiencia_anios": 0,
                "disponibilidad_horas_semana": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.username, "editar_user")