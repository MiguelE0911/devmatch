from types import SimpleNamespace

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.admin import UsuarioAdmin, UsuarioChangeForm
from apps.accounts.models import Usuario


class UsuarioChangeFormTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "bloq@devmatch.test", "bloq", password="Clave-123!"
        )

    def _datos(self, **overrides):
        datos = {
            "email": self.usuario.email,
            "username": self.usuario.username,
            "first_name": "",
            "last_name": "",
            "es_activo": "on",
        }
        datos.update(overrides)
        return datos

    def test_bloquear_sin_motivo_se_rechaza(self):
        form = UsuarioChangeForm(
            data=self._datos(esta_bloqueado="on"), instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn("motivo_bloqueo", form.errors)

    def test_un_motivo_solo_con_espacios_se_rechaza(self):
        form = UsuarioChangeForm(
            data=self._datos(esta_bloqueado="on", motivo_bloqueo="   "),
            instance=self.usuario,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("motivo_bloqueo", form.errors)

    def test_bloquear_con_motivo_es_valido(self):
        form = UsuarioChangeForm(
            data=self._datos(esta_bloqueado="on", motivo_bloqueo="Spam reiterado"),
            instance=self.usuario,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_sin_bloquear_no_se_exige_motivo(self):
        form = UsuarioChangeForm(data=self._datos(), instance=self.usuario)
        self.assertTrue(form.is_valid(), form.errors)


class UsuarioAdminBloqueoTests(TestCase):
    def setUp(self):
        self.supervisor = Usuario.objects.create_superuser(
            "super@devmatch.test", "super", password="Clave-123!"
        )
        self.objetivo = Usuario.objects.create_user(
            "objetivo@devmatch.test", "objetivo", password="Clave-123!"
        )
        self.admin = UsuarioAdmin(Usuario, site)
        self.request = RequestFactory().post("/")
        self.request.user = self.supervisor

    def test_save_model_registra_quien_y_cuando_bloquea(self):
        self.objetivo.esta_bloqueado = True
        self.objetivo.motivo_bloqueo = "Spam"
        form = SimpleNamespace(changed_data=["esta_bloqueado", "motivo_bloqueo"])
        self.admin.save_model(self.request, self.objetivo, form, change=True)

        self.objetivo.refresh_from_db()
        self.assertEqual(self.objetivo.bloqueado_por, self.supervisor)
        self.assertIsNotNone(self.objetivo.bloqueado_en)

    def test_save_model_no_cambia_quien_bloqueo_si_solo_se_edita_el_motivo(self):
        otro = Usuario.objects.create_user(
            "otro@devmatch.test", "otro", password="Clave-123!"
        )
        self.objetivo.esta_bloqueado = True
        self.objetivo.motivo_bloqueo = "Spam"
        self.objetivo.bloqueado_por = otro
        self.objetivo.save()

        self.objetivo.motivo_bloqueo = "Spam y acoso"
        form = SimpleNamespace(changed_data=["motivo_bloqueo"])
        self.admin.save_model(self.request, self.objetivo, form, change=True)

        self.objetivo.refresh_from_db()
        self.assertEqual(self.objetivo.bloqueado_por, otro)

    def test_save_model_registra_quien_y_cuando_desactiva(self):
        self.objetivo.es_activo = False
        form = SimpleNamespace(changed_data=["es_activo"])
        self.admin.save_model(self.request, self.objetivo, form, change=True)

        self.objetivo.refresh_from_db()
        self.assertEqual(self.objetivo.desactivado_por, self.supervisor)
        self.assertIsNotNone(self.objetivo.desactivado_en)

    def test_save_model_no_cambia_la_desactivacion_si_no_cambia_es_activo(self):
        otro = Usuario.objects.create_user(
            "otro2@devmatch.test", "otro2", password="Clave-123!"
        )
        self.objetivo.es_activo = False
        self.objetivo.desactivado_por = otro
        self.objetivo.save()

        self.objetivo.first_name = "Nuevo"
        form = SimpleNamespace(changed_data=["first_name"])
        self.admin.save_model(self.request, self.objetivo, form, change=True)

        self.objetivo.refresh_from_db()
        self.assertEqual(self.objetivo.desactivado_por, otro)

    def test_los_campos_que_pone_el_sistema_son_de_solo_lectura(self):
        for campo in (
            "bloqueado_en",
            "bloqueado_por",
            "desactivado_en",
            "desactivado_por",
        ):
            with self.subTest(campo=campo):
                self.assertIn(campo, self.admin.readonly_fields)

    def test_el_admin_no_ofrece_borrado_fisico(self):
        self.assertFalse(self.admin.has_delete_permission(self.request, self.objetivo))
        acciones = self.admin.get_actions(self.request)
        self.assertNotIn("delete_selected", acciones)
        self.assertIn("desactivar_usuarios", acciones)


class DesactivarUsuariosAccionTests(TestCase):
    def setUp(self):
        self.supervisor = Usuario.objects.create_superuser(
            "super2@devmatch.test", "super2", password="Clave-123!"
        )
        self.objetivo = Usuario.objects.create_user(
            "objetivo2@devmatch.test", "objetivo2", password="Clave-123!"
        )
        self.client.force_login(self.supervisor)

    def _ejecutar(self, *usuarios):
        return self.client.post(
            reverse("admin:accounts_usuario_changelist"),
            {
                "action": "desactivar_usuarios",
                "_selected_action": [u.pk for u in usuarios],
                "index": 0,
            },
            follow=True,
        )

    def test_desactiva_sin_borrar_y_registra_quien_y_cuando(self):
        self._ejecutar(self.objetivo)
        self.objetivo.refresh_from_db()
        self.assertFalse(self.objetivo.es_activo)
        self.assertEqual(self.objetivo.desactivado_por, self.supervisor)
        self.assertIsNotNone(self.objetivo.desactivado_en)
        self.assertTrue(Usuario.objects.filter(pk=self.objetivo.pk).exists())

    def test_no_permite_desactivar_la_propia_cuenta(self):
        self._ejecutar(self.objetivo, self.supervisor)
        self.supervisor.refresh_from_db()
        self.objetivo.refresh_from_db()
        self.assertTrue(self.supervisor.es_activo)
        self.assertFalse(self.objetivo.es_activo)