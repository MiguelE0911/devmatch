from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

Usuario = get_user_model()


class AccountStateMiddlewareTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "activo@devmatch.test", "activo", password="Clave-123!"
        )
        self.feed = reverse("core:feed")
        self.login = reverse("accounts:login")

    def test_usuario_activo_accede_normalmente(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.feed)
        self.assertEqual(response.status_code, 200)

    def test_usuario_bloqueado_se_desloguea_y_es_redirigido(self):
        self.client.force_login(self.usuario)
        self.usuario.esta_bloqueado = True
        self.usuario.save(update_fields=["esta_bloqueado"])
        response = self.client.get(self.feed)
        self.assertRedirects(response, self.login)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_desactivado_se_desloguea_y_es_redirigido(self):
        self.client.force_login(self.usuario)
        self.usuario.es_activo = False
        self.usuario.save(update_fields=["es_activo"])
        response = self.client.get(self.feed)
        self.assertRedirects(response, self.login)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_reactivar_la_cuenta_no_reutiliza_la_sesion_colgante(self):
        self.client.force_login(self.usuario)
        self.usuario.esta_bloqueado = True
        self.usuario.save(update_fields=["esta_bloqueado"])
        # El primer acceso ya cierra y limpia la sesión.
        self.client.get(self.feed)
        # Al reactivar, la cookie vieja no debe volver a autenticar.
        self.usuario.esta_bloqueado = False
        self.usuario.save(update_fields=["esta_bloqueado"])
        response = self.client.get(self.feed)
        self.assertRedirects(response, f"{self.login}?next={self.feed}")

    def test_anonimo_no_es_afectado_por_el_middleware(self):
        response = self.client.get(self.feed)
        self.assertRedirects(response, f"{self.login}?next={self.feed}")
        self.assertNotIn("_auth_user_id", self.client.session)
