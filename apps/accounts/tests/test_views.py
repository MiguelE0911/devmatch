from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
        self.assertContains(resp, "3 a 30 caracteres")
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