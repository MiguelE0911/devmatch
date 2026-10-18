"""Tests de apps.projects.media_utils.

Usa SimpleTestCase (sin BD): procesar_imagen y guardar_imagen solo tocan
Pillow y MEDIA_ROOT, que se apunta a un temporal por test. Todas las
imágenes se generan en memoria con Pillow; no hay ficheros del repo.
"""

import io
import os
import tempfile
from unittest.mock import PropertyMock, patch

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.projects.media_utils import LIMITE_MB, MAX_PX, guardar_imagen, procesar_imagen


def _crear_bytes(formato, ancho=64, alto=64, color=(180, 40, 60), **kwargs):
    buf = io.BytesIO()
    Image.new("RGB", (ancho, alto), color).save(buf, formato, **kwargs)
    return buf.getvalue()


class _BaseMedia(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.media_root = self._tmp.name
        ajustes = override_settings(MEDIA_ROOT=self.media_root, MEDIA_URL="/media/")
        ajustes.enable()
        self.addCleanup(ajustes.disable)

    def _subido(self, nombre, datos, content_type="image/png"):
        return SimpleUploadedFile(nombre, datos, content_type=content_type)

    def _leer(self, content_file):
        content_file.seek(0)
        return content_file.read()


class ProcesarImagenTests(_BaseMedia):
    def test_png_valido_devuelve_content_file_con_nombre_aleatorio(self):
        archivo = self._subido("foto.png", _crear_bytes("PNG"))
        resultado = procesar_imagen(archivo, "prototipo")
        self.assertIsInstance(resultado, ContentFile)
        self.assertRegex(resultado.name, r"^prototipo-[0-9a-f]{8}\.png$")

    def test_jpeg_valido_se_procesa_con_extension_jpg(self):
        archivo = self._subido("foto.jpg", _crear_bytes("JPEG"), "image/jpeg")
        resultado = procesar_imagen(archivo, "prototipo")
        self.assertIsInstance(resultado, ContentFile)
        self.assertRegex(resultado.name, r"^prototipo-[0-9a-f]{8}\.jpg$")
        reabierta = Image.open(io.BytesIO(self._leer(resultado)))
        self.assertEqual(reabierta.format, "JPEG")

    def test_archivo_que_no_es_imagen_lanza_validation_error(self):
        archivo = self._subido("x.png", b"esto no es una imagen, solo texto plano")
        with self.assertRaises(ValidationError) as ctx:
            procesar_imagen(archivo, "prototipo")
        self.assertIn("imagen", " ".join(ctx.exception.messages))

    def test_bmp_lanza_error_de_formato_no_soportado(self):
        archivo = self._subido("foto.bmp", _crear_bytes("BMP"), "image/bmp")
        with self.assertRaises(ValidationError) as ctx:
            procesar_imagen(archivo, "prototipo")
        self.assertIn("Formato no soportado", " ".join(ctx.exception.messages))

    def test_svg_lanza_validation_error(self):
        svg = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            b"<rect width=\"10\" height=\"10\"/></svg>"
        )
        archivo = self._subido("x.svg", svg, "image/svg+xml")
        with self.assertRaises(ValidationError):
            procesar_imagen(archivo, "prototipo")

    def test_peso_excedido_lanza_validation_error(self):
        archivo = self._subido("logo.png", _crear_bytes("PNG"))
        exceso = LIMITE_MB["logo"] * 1024 * 1024 + 1
        with patch.object(
            SimpleUploadedFile, "size", new_callable=PropertyMock
        ) as mock_size:
            mock_size.return_value = exceso
            with self.assertRaises(ValidationError) as ctx:
                procesar_imagen(archivo, "logo")
        self.assertIn("no puede pesar más de", " ".join(ctx.exception.messages))
        self.assertIn(f"{LIMITE_MB['logo']} MB", " ".join(ctx.exception.messages))

    def test_tipo_invalido_lanza_validation_error(self):
        archivo = self._subido("foto.png", _crear_bytes("PNG"))
        with self.assertRaises(ValidationError):
            procesar_imagen(archivo, "avatar")
        with self.assertRaises(ValidationError):
            guardar_imagen(1, "avatar", ContentFile(b"x", name="foto.png"))

    def test_logo_grande_se_redimensiona_al_maximo(self):
        archivo = self._subido("logo.png", _crear_bytes("PNG", 900, 900))
        resultado = procesar_imagen(archivo, "logo")
        reabierta = Image.open(io.BytesIO(self._leer(resultado)))
        self.assertLessEqual(max(reabierta.size), MAX_PX["logo"])

    def test_gif_animado_se_devuelve_byte_a_byte_identico(self):
        buf = io.BytesIO()
        frame1 = Image.new("RGB", (20, 20), (255, 0, 0))
        frame2 = Image.new("RGB", (20, 20), (0, 0, 255))
        frame1.save(
            buf, "GIF", save_all=True, append_images=[frame2], duration=100, loop=0
        )
        gif_bytes = buf.getvalue()
        archivo = self._subido("anim.gif", gif_bytes, "image/gif")
        resultado = procesar_imagen(archivo, "prototipo")
        self.assertRegex(resultado.name, r"^prototipo-[0-9a-f]{8}\.gif$")
        self.assertEqual(self._leer(resultado), gif_bytes)


class GuardarImagenTests(_BaseMedia):
    def test_guardar_imagen_persiste_el_archivo_y_devuelve_url(self):
        archivo = self._subido("foto.png", _crear_bytes("PNG"))
        procesado = procesar_imagen(archivo, "prototipo")
        url = guardar_imagen(1, "prototipo", procesado)
        self.assertTrue(url.startswith("/media/proyectos/1/"))
        ruta_en_disco = os.path.join(
            self.media_root, "proyectos", "1", os.path.basename(url)
        )
        self.assertTrue(os.path.isfile(ruta_en_disco), ruta_en_disco)

    def test_guardar_imagen_sin_nombre_lanza_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            guardar_imagen(1, "prototipo", ContentFile(b""))
        self.assertIn("no está procesado", " ".join(ctx.exception.messages))
