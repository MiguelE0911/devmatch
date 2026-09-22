from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.forms import LoginForm, RegistroForm

Usuario = get_user_model()

VALID = {
    "username": "dev_test",
    "email": "nuevo@devmatch.test",
    "first_name": "Ana",
    "last_name": "Ríos",
    "password1": "Clave-Segura-99!",
    "password2": "Clave-Segura-99!",
}


def valid_data(**overrides):
    data = dict(VALID)
    data.update(overrides)
    return data


class RegistroFormTests(TestCase):
    def test_registro_valido_guarda_usuario_y_password_hasheado(self):
        form = RegistroForm(data=valid_data())
        self.assertTrue(form.is_valid(), form.errors.as_text())

        usuario = form.save()

        self.assertEqual(usuario.email, "nuevo@devmatch.test")
        self.assertFalse(usuario.es_admin)
        self.assertTrue(usuario.es_activo)
        self.assertNotEqual(usuario.password, VALID["password1"])
        self.assertTrue(usuario.check_password(VALID["password1"]))

    def test_normaliza_dominio_a_minusculas(self):
        form = RegistroForm(data=valid_data(email="Nuevo@DevMatch.TEST"))
        self.assertTrue(form.is_valid(), form.errors.as_text())
        # La parte local conserva mayúsculas (RFC); el dominio se normaliza.
        self.assertEqual(form.cleaned_data["email"], "Nuevo@devmatch.test")

    def test_todos_los_campos_son_obligatorios(self):
        form = RegistroForm(
            data={
                "username": "",
                "email": "",
                "first_name": "",
                "last_name": "",
                "password1": "",
                "password2": "",
            }
        )
        self.assertFalse(form.is_valid())
        for campo in ("username", "email", "first_name", "last_name", "password1", "password2"):
            self.assertIn(campo, form.errors)

    def test_username_con_formato_invalido(self):
        form = RegistroForm(data=valid_data(username="mal usuario!"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_username_demasiado_corto(self):
        form = RegistroForm(data=valid_data(username="ab"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_email_invalido(self):
        form = RegistroForm(data=valid_data(email="no-es-un-correo"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_username_duplicado_insensible_a_mayusculas(self):
        Usuario.objects.create_user("repo@devmatch.test", "Dev_Test", password="x-Clave-99!")
        form = RegistroForm(data=valid_data(username="dev_test"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_email_duplicado_insensible_a_mayusculas(self):
        Usuario.objects.create_user("dup@devmatch.test", "repo", password="x-Clave-99!")
        form = RegistroForm(data=valid_data(email="DUP@devmatch.test"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_que_no_coincide(self):
        form = RegistroForm(data=valid_data(password2="Otra-Clave-99!"))
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_password_debil_numerica(self):
        form = RegistroForm(data=valid_data(password1="12345678", password2="12345678"))
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_password_similar_al_username(self):
        form = RegistroForm(data=valid_data(password1="dev_test_dev", password2="dev_test_dev"))
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class LoginFormTests(TestCase):
    def test_autentica_por_email(self):
        Usuario.objects.create_user(
            "login@devmatch.test", "login_user", password="Clave-Segura-99!"
        )
        form = LoginForm(
            data={"username": "login@devmatch.test", "password": "Clave-Segura-99!"}
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.get_user().email, "login@devmatch.test")

    def test_autentica_por_username(self):
        Usuario.objects.create_user(
            "login@devmatch.test", "login_user", password="Clave-Segura-99!"
        )
        form = LoginForm(
            data={"username": "login_user", "password": "Clave-Segura-99!"}
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.get_user().email, "login@devmatch.test")

    def test_autentica_por_username_insensible_a_mayusculas(self):
        Usuario.objects.create_user(
            "login@devmatch.test", "login_user", password="Clave-Segura-99!"
        )
        form = LoginForm(
            data={"username": "  LOGIN_User ", "password": "Clave-Segura-99!"}
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.get_user().email, "login@devmatch.test")

    def test_error_generico_si_ni_email_ni_username_existen(self):
        form = LoginForm(
            data={"username": "no_existo", "password": "incorrecta"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Correo electrónico o contraseña incorrectos.",
            form.errors["__all__"],
        )

    def test_error_generico_con_claves_invalidas(self):
        form = LoginForm(
            data={"username": "cualquiera@devmatch.test", "password": "incorrecta"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Correo electrónico o contraseña incorrectos.",
            form.errors["__all__"],
        )

    def test_mensaje_generico_para_cuenta_inactiva(self):
        usuario = Usuario.objects.create_user(
            "inactiva@devmatch.test", "inactiva", password="Clave-Segura-99!"
        )
        usuario.es_activo = False
        usuario.save(update_fields=["es_activo"])

        form = LoginForm(
            data={"username": "inactiva@devmatch.test", "password": "Clave-Segura-99!"}
        )
        self.assertFalse(form.is_valid())
        # No debe filtrar el estado de la cuenta: mismo mensaje genérico.
        self.assertIn(ERROR := "Correo electrónico o contraseña incorrectos.", form.errors["__all__"])
        self.assertEqual(len(form.errors["__all__"]), 1)