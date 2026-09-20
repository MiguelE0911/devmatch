from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, TestCase

from apps.core import permissions
from apps.core.mixins import ProjectCreatorRequiredMixin
from apps.projects.models import Proyecto, Vacante

Usuario = get_user_model()


class BasePermisosTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.creador = Usuario.objects.create_user(
            "creador-p@devmatch.test", "creador-p", password="Clave-123!"
        )
        self.otro = Usuario.objects.create_user(
            "otro-p@devmatch.test", "otro-p", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def _request_de(self, user):
        request = self.factory.get("/x/")
        request.session = {}
        request.user = user
        return request


class EsCreadorTests(BasePermisosTests):
    def test_el_creador_autenticado_tiene_permiso(self):
        self.assertTrue(permissions.es_creador(self.creador, self.proyecto))

    def test_un_usuario_distinto_no_tiene_permiso(self):
        self.assertFalse(permissions.es_creador(self.otro, self.proyecto))

    def test_usuario_anonimo_no_tiene_permiso(self):
        self.assertFalse(permissions.es_creador(None, self.proyecto))

    def test_sin_objeto_no_tiene_permiso(self):
        self.assertFalse(permissions.es_creador(self.creador, None))

    def test_subentidad_con_fk_proyecto_resuelve_al_creador(self):
        vacante = Vacante.objects.create(
            proyecto=self.proyecto,
            titulo="Backend",
            descripcion="desc",
            cupos_totales=2,
        )
        self.assertTrue(permissions.es_creador(self.creador, vacante))
        self.assertFalse(permissions.es_creador(self.otro, vacante))


class ProjectCreatorRequiredMixinTests(BasePermisosTests):
    def _vista(self, objeto):
        class _Vista(ProjectCreatorRequiredMixin):
            def __init__(self, obj):
                self._objeto = obj

            def get_object(self):
                return self._objeto

        vista = _Vista(objeto)
        vista.request = self._request_de(self.otro)
        return vista

    def test_creador_autenticado_pasa(self):
        vista = self._vista(self.proyecto)
        vista.request.user = self.creador
        self.assertTrue(vista.test_func())

    def test_otro_usuario_no_pasa(self):
        self.assertFalse(self._vista(self.proyecto).test_func())

    def test_anonimo_no_pasa(self):
        vista = self._vista(self.proyecto)
        vista.request.user = None
        self.assertFalse(vista.test_func())

    def test_sin_objeto_no_pasa(self):
        self.assertFalse(self._vista(None).test_func())

    def test_funciona_con_vacante_del_proyecto(self):
        vacante = Vacante.objects.create(
            proyecto=self.proyecto,
            titulo="Backend",
            descripcion="desc",
            cupos_totales=2,
        )
        vista = self._vista(vacante)
        vista.request.user = self.creador
        self.assertTrue(vista.test_func())


class CreadorRequiredDecoratorTests(BasePermisosTests):
    @permissions.creador_required(Proyecto)
    def _vista_proyecto(self, request, pk):
        return HttpResponse("ok")

    def test_creador_pasa_y_ejecuta_la_vista(self):
        request = self._request_de(self.creador)
        response = self._vista_proyecto(request, pk=self.proyecto.pk)
        self.assertEqual(response.status_code, 200)

    def test_usuario_distinto_se_redirige_a_login(self):
        request = self._request_de(self.otro)
        response = self._vista_proyecto(request, pk=self.proyecto.pk)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)

    def test_anonimo_se_redirige_a_login(self):
        request = self._request_de(None)
        response = self._vista_proyecto(request, pk=self.proyecto.pk)
        self.assertIsInstance(response, HttpResponseRedirect)

    def test_objeto_inexistente_se_redirige(self):
        request = self._request_de(self.creador)
        response = self._vista_proyecto(request, pk=999999)
        self.assertIsInstance(response, HttpResponseRedirect)