"""Tests de los flujos de subida de imágenes (formulario y vista).

Formularios: `ProyectoMediaForm` (galería, híbrido archivo/URL) y
`ProyectoForm` (logo). Vistas: `ProyectoGaleriaEditView` y
`ProyectoCreateView`. Las imágenes se generan en memoria con Pillow y se
guardan en un MEDIA_ROOT temporal (override_settings + cleanup); ningún
fichero del repo se ensucia. TestCase normal porque las vistas/formularios
toquetean la BD de pruebas (Neon).
"""

import io
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.projects.forms import ProyectoForm, ProyectoMediaForm
from apps.projects.models import Proyecto, ProyectoMedia

Usuario = get_user_model()


def _png_bytes(ancho=64, alto=64, color=(180, 40, 60)):
    buf = io.BytesIO()
    Image.new("RGB", (ancho, alto), color).save(buf, "PNG")
    return buf.getvalue()


class _BaseUploads(TestCase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.media_root = self._tmp.name
        ajustes = override_settings(MEDIA_ROOT=self.media_root, MEDIA_URL="/media/")
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.creador = Usuario.objects.create_user(
            "creador-uploads@devmatch.test", "creador-uploads", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )

    def _png(self, nombre="foto.png"):
        return SimpleUploadedFile(nombre, _png_bytes(), content_type="image/png")

    def _ruta_en_disco(self, url):
        """Ruta real bajo MEDIA_ROOT para una URL /media/... devuelta por storage."""
        return os.path.join(self.media_root, *url.removeprefix("/media/").split("/"))


class ProyectoMediaFormSubidaTests(_BaseUploads):
    """A) ProyectoMediaForm: archivo procesado, URL externa e híbrido."""

    def _form(self, data=None, files=None):
        return ProyectoMediaForm(
            data=data or {}, files=files or {}, proyecto=self.proyecto
        )

    def _guardar(self, form):
        # El formulario no conoce proyecto/tipo (los pone la vista); aquí se
        # fijan en la instancia igual que hace ProyectoGaleriaEditView.
        form.instance.proyecto = self.proyecto
        form.instance.tipo = ProyectoMedia.TIPO_PROTOTIPO
        return form.save()

    def test_subida_valida_guarda_el_archivo_y_escribe_la_url_local(self):
        form = self._form(files={"archivo": self._png()})
        self.assertTrue(form.is_valid(), form.errors)
        media = self._guardar(form)
        self.assertTrue(
            media.archivo_url.startswith(f"/media/proyectos/{self.proyecto.pk}/"),
            media.archivo_url,
        )
        self.assertTrue(os.path.isfile(self._ruta_en_disco(media.archivo_url)))

    def test_solo_url_externa_se_conserva_tal_cual(self):
        url = "https://example.com/captura.png"
        form = self._form(data={"archivo_url": url})
        self.assertTrue(form.is_valid(), form.errors)
        media = self._guardar(form)
        self.assertEqual(media.archivo_url, url)

    def test_archivo_y_url_a_la_vez_gana_el_archivo(self):
        form = self._form(
            data={"archivo_url": "https://example.com/captura.png"},
            files={"archivo": self._png()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        media = self._guardar(form)
        self.assertTrue(media.archivo_url.startswith("/media/"), media.archivo_url)

    def test_ni_archivo_ni_url_es_invalido(self):
        form = self._form()
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_archivo_falso_con_nombre_png_es_invalido(self):
        falso = SimpleUploadedFile("x.png", b"texto plano", content_type="image/png")
        form = self._form(files={"archivo": falso})
        self.assertFalse(form.is_valid())
        self.assertIn("archivo", form.errors)

    def test_url_con_formato_invalido_es_invalida(self):
        form = self._form(data={"archivo_url": "no-sirve"})
        self.assertFalse(form.is_valid())
        self.assertIn("archivo_url", form.errors)


class ProyectoFormLogoTests(_BaseUploads):
    """B) ProyectoForm: logo subido, solo logo_url y logo falso."""

    def _datos(self, **cambios):
        datos = {
            "nombre": self.proyecto.nombre,
            "descripcion": self.proyecto.descripcion,
            "logo_url": self.proyecto.logo_url or "",
            "estado": self.proyecto.estado,
        }
        datos.update(cambios)
        return datos

    def test_logo_subido_escribe_logo_url_local_y_guarda_el_archivo(self):
        form = ProyectoForm(
            instance=self.proyecto,
            data=self._datos(),
            files={"logo": self._png("logo.png")},
        )
        self.assertTrue(form.is_valid(), form.errors)
        proyecto = form.save()
        proyecto.refresh_from_db()
        self.assertTrue(
            proyecto.logo_url.startswith(f"/media/proyectos/{proyecto.pk}/"),
            proyecto.logo_url,
        )
        self.assertTrue(os.path.isfile(self._ruta_en_disco(proyecto.logo_url)))

    def test_solo_logo_url_texto_se_conserva(self):
        url = "https://example.com/logo.png"
        form = ProyectoForm(instance=self.proyecto, data=self._datos(logo_url=url))
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.logo_url, url)

    def test_logo_falso_con_nombre_png_es_invalido(self):
        falso = SimpleUploadedFile("logo.png", b"texto plano", content_type="image/png")
        form = ProyectoForm(
            instance=self.proyecto, data=self._datos(), files={"logo": falso}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("logo", form.errors)


class GaleriaSubidaViewTests(_BaseUploads):
    """C10) ProyectoGaleriaEditView con archivo multipart."""

    def test_post_del_creador_con_archivo_crea_prototipo_activo(self):
        self.client.force_login(self.creador)
        resp = self.client.post(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk]),
            {"archivo_url": "", "orden": "", "archivo": self._png()},
        )
        self.assertRedirects(
            resp,
            reverse("projects:project_detail", args=[self.proyecto.pk])
            + "?tab=galeria",
        )
        media = ProyectoMedia.objects.get()
        self.assertEqual(media.proyecto, self.proyecto)
        self.assertEqual(media.tipo, ProyectoMedia.TIPO_PROTOTIPO)
        self.assertTrue(media.es_activo)
        self.assertTrue(media.archivo_url.startswith("/media/"), media.archivo_url)
        self.assertTrue(os.path.isfile(self._ruta_en_disco(media.archivo_url)))


class ProyectoCreateSubidaViewTests(_BaseUploads):
    """C11/C12) ProyectoCreateView con y sin archivo de logo."""

    def test_post_con_archivo_crea_el_proyecto_con_logo_url_local(self):
        self.client.force_login(self.creador)
        resp = self.client.post(
            reverse("projects:project_create"),
            {
                "nombre": "Nuevo con logo",
                "descripcion": "desc",
                "logo_url": "",
                "logo": self._png("logo.png"),
            },
        )
        self.assertEqual(resp.status_code, 302)
        proyecto = Proyecto.objects.get(nombre="Nuevo con logo")
        self.assertEqual(
            resp.url, reverse("projects:project_detail", args=[proyecto.pk])
        )
        self.assertTrue(
            proyecto.logo_url.startswith(f"/media/proyectos/{proyecto.pk}/"),
            proyecto.logo_url,
        )
        self.assertTrue(os.path.isfile(self._ruta_en_disco(proyecto.logo_url)))

    def test_post_solo_logo_url_texto_lo_conserva(self):
        self.client.force_login(self.creador)
        resp = self.client.post(
            reverse("projects:project_create"),
            {
                "nombre": "Nuevo con url",
                "descripcion": "desc",
                "logo_url": "https://example.com/logo.png",
            },
        )
        self.assertEqual(resp.status_code, 302)
        proyecto = Proyecto.objects.get(nombre="Nuevo con url")
        self.assertEqual(proyecto.logo_url, "https://example.com/logo.png")
