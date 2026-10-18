"""Procesamiento de imágenes subidas por los usuarios (logos y prototipos).

Pillow valida el archivo REAL (nunca el content_type declarado, que es
falsificable), lo normaliza y devuelve un ContentFile listo para guardarse
en MEDIA_ROOT. La URL resultante ("/media/proyectos/<id>/...") es lo que se
escribe en `proyecto_media.archivo_url` y `proyectos.logo_url` — columnas
TEXT del esquema oficial, que no tiene columna de archivo (ver DevMatch-BD
5.2): la ruta relativa ES el dato, por eso el modelo no cambia ni hay
migración.

Formatos: JPG, PNG, WEBP y GIF. El GIF se valida pero no se re-codifica para
conservar la animación; el resto se re-codifica al mismo formato sin
metadatos (elimina EXIF y cualquier payload incrustado).
"""

import io
import os
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps
from PIL.Image import DecompressionBombError, UnidentifiedImageError

LIMITE_MB = {"logo": 2, "prototipo": 5}
MAX_PX = {"logo": 512, "prototipo": 1920}
EXTENSIONES = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}
MAX_PIXELES = 40_000_000


def _validar_tipo(tipo):
    if tipo not in LIMITE_MB:
        raise ValidationError("Tipo de imagen no válido.")


def _mensaje_peso(tipo):
    sujeto = "El logo" if tipo == "logo" else "La imagen"
    return f"{sujeto} no puede pesar más de {LIMITE_MB[tipo]} MB."


def procesar_imagen(archivo, tipo):
    """Valida `archivo` con Pillow y devuelve un ContentFile normalizado.

    El nombre del ContentFile es `{tipo}-{8 hex}.ext` (minúsculas). Lanza
    ValidationError (en español) ante cualquier problema: el formulario la
    muestra como error de campo. Ver docstring de módulo para las reglas.
    """
    _validar_tipo(tipo)
    if archivo is None:
        raise ValidationError("No se recibió ningún archivo.")

    if archivo.size > LIMITE_MB[tipo] * 1024 * 1024:
        raise ValidationError(_mensaje_peso(tipo))

    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen.verify()
    except DecompressionBombError:
        raise ValidationError("La imagen tiene dimensiones demasiado grandes.")
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("El archivo no es una imagen válida o está dañado.")

    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
    except DecompressionBombError:
        raise ValidationError("La imagen tiene dimensiones demasiado grandes.")
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("El archivo no es una imagen válida o está dañado.")

    formato = (imagen.format or "").upper()
    if formato not in EXTENSIONES:
        raise ValidationError("Formato no soportado. Sube una imagen JPG, PNG, WEBP o GIF.")

    if imagen.width * imagen.height > MAX_PIXELES:
        raise ValidationError("La imagen tiene dimensiones demasiado grandes.")

    if formato == "GIF":
        try:
            imagen.load()
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError("El archivo no es una imagen válida o está dañado.")
        archivo.seek(0)
        return ContentFile(
            archivo.read(), name=f"{tipo}-{uuid.uuid4().hex[:8]}.gif"
        )

    try:
        imagen = ImageOps.exif_transpose(imagen)
        max_px = MAX_PX[tipo]
        if max(imagen.size) > max_px:
            imagen.thumbnail((max_px, max_px), Image.LANCZOS)

        if formato == "JPEG" and imagen.mode not in ("RGB", "L"):
            if imagen.mode in ("RGBA", "LA", "P"):
                base = Image.new("RGB", imagen.size, (255, 255, 255))
                rgba = imagen.convert("RGBA")
                base.paste(rgba, mask=rgba.getchannel("A"))
                imagen = base
            else:
                imagen = imagen.convert("RGB")

        buffer = io.BytesIO()
        if formato == "JPEG":
            imagen.save(buffer, format="JPEG", optimize=True, quality=85)
        elif formato == "WEBP":
            imagen.save(buffer, format="WEBP", quality=85, method=4)
        else:
            imagen.save(buffer, format="PNG", optimize=True)
    except DecompressionBombError:
        raise ValidationError("La imagen tiene dimensiones demasiado grandes.")
    except (OSError, ValueError):
        raise ValidationError("El archivo no es una imagen válida o está dañado.")

    nombre = f"{tipo}-{uuid.uuid4().hex[:8]}.{EXTENSIONES[formato]}"
    return ContentFile(buffer.getvalue(), name=nombre)


def guardar_imagen(proyecto_id, tipo, archivo_procesado):
    """Guarda un archivo YA procesado en `media/proyectos/<id>/` y devuelve
    su URL relativa ("/media/proyectos/<id>/<nombre>"), que es el valor que
    se escribe en `archivo_url` / `logo_url`.
    """
    _validar_tipo(tipo)
    if not proyecto_id:
        raise ValidationError("No se indicó el proyecto de la imagen.")
    nombre = getattr(archivo_procesado, "name", "") or ""
    if not nombre:
        raise ValidationError("El archivo no está procesado.")
    # Defensa: nunca confiar en el nombre del caller, aunque hoy lo genere
    # procesar_imagen (evita path traversal si un futuro código pasa el
    # nombre original del usuario).
    nombre = os.path.basename(nombre.replace("\\", "/"))
    ruta = f"proyectos/{proyecto_id}/{nombre}"
    guardado = default_storage.save(ruta, archivo_procesado)
    url = default_storage.url(guardado)
    # MEDIA_URL del repo es "media/" (sin barra inicial); las plantillas y el
    # seed usan rutas con "/" inicial, así que se normaliza aquí.
    return url if url.startswith("/") else f"/{url}"
