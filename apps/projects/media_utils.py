"""Procesamiento de imágenes subidas por los usuarios (logos y prototipos).

Pillow valida el archivo REAL (nunca el content_type declarado, que es
falsificable), lo normaliza y devuelve un ContentFile listo para guardarse.
El destino lo decide `guardar_imagen`: Neon Object Storage (bucket público
del equipo, si las 5 vars de storage están en el entorno) o MEDIA_ROOT
local como fallback. En ambos casos la URL resultante es lo que se escribe
en `proyecto_media.archivo_url` y `proyectos.logo_url` — columnas TEXT del
esquema oficial, que no tiene columna de archivo (ver DevMatch-BD 5.2): la
URL ES el dato, por eso el modelo no cambia ni hay migración.

Formatos: JPG, PNG, WEBP y GIF. El GIF se valida pero no se re-codifica para
conservar la animación; el resto se re-codifica al mismo formato sin
metadatos (elimina EXIF y cualquier payload incrustado).
"""

import io
import os
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps
from PIL.Image import DecompressionBombError, UnidentifiedImageError

LIMITE_MB = {"logo": 2, "prototipo": 5}
MAX_PX = {"logo": 512, "prototipo": 1920}
EXTENSIONES = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}
MAX_PIXELES = 40_000_000
CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}
# Los nombres de archivo son aleatorios (uuid), así que el navegador puede
# cachear agresivamente: reemplazar una imagen genera una URL nueva.
CACHE_CONTROL = "public, max-age=2678400"  # 31 días


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


def _neon_storage():
    """Devuelve (endpoint, bucket, clave, secreta, region) con las 5 vars ya
    saneadas si Neon Object Storage está configurado; None si falta alguna o
    el endpoint no es https (modo local). El MISMO tuple se usa para crear el
    cliente y para componer la URL pública: evita que un espacio residual del
    .env desajuste la firma SigV4 contra la URL servida, y que un endpoint
    http tipeado firmen en claro.
    """
    endpoint = (settings.AWS_ENDPOINT_URL_S3 or "").strip()
    bucket = (settings.NEON_STORAGE_BUCKET or "").strip()
    clave = (settings.AWS_ACCESS_KEY_ID or "").strip()
    secreta = (settings.AWS_SECRET_ACCESS_KEY or "").strip()
    region = (settings.AWS_REGION or "").strip()
    if not all((endpoint, bucket, clave, secreta, region)):
        return None
    if not endpoint.startswith("https://"):
        return None
    return endpoint, bucket, clave, secreta, region


def _subir_a_neon(config, clave, contenido, extension):
    """Sube un objeto al bucket y devuelve su URL pública. Lanza
    ValidationError si el storage rechaza la operación (el error original no
    se encadena para no dejar endpoint/bucket/request-id en el traceback).
    """
    endpoint, bucket, access, secret, region = config
    cliente = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        # Neon Object Storage solo soporta path-style y SigV4.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    try:
        cliente.put_object(
            Bucket=bucket,
            Key=clave,
            Body=contenido,
            ContentType=CONTENT_TYPES.get(extension, "application/octet-stream"),
            CacheControl=CACHE_CONTROL,
        )
    except (BotoCoreError, ClientError):
        raise ValidationError(
            "No se pudo guardar la imagen en el storage. Inténtalo de nuevo."
        ) from None
    finally:
        cliente.close()
    # Nota: put_object sobrescribe ante colisión de clave (a diferencia de
    # default_storage, que renombra). Con nombre uuid de 8 hex dentro de la
    # carpeta de cada proyecto, la colisión es despreciable para este proyecto.
    return f"{endpoint}/{bucket}/{clave}"


def guardar_imagen(proyecto_id, tipo, archivo_procesado):
    """Guarda un archivo YA procesado y devuelve su URL.

    Con Neon Object Storage configurado sube al bucket `public_read` y
    devuelve la URL pública ("https://<branch>.storage.../<bucket>/...").
    Sin configurar (o si el teammate no tiene credencial), guarda en
    `media/proyectos/<id>/` y devuelve la URL relativa ("/media/...").
    En ambos casos esa URL es el valor que se escribe en `archivo_url` /
    `logo_url`.
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
    clave = f"proyectos/{proyecto_id}/{nombre}"

    config = _neon_storage()
    if config:
        archivo_procesado.seek(0)
        extension = nombre.rsplit(".", 1)[-1].lower()
        return _subir_a_neon(config, clave, archivo_procesado.read(), extension)

    guardado = default_storage.save(clave, archivo_procesado)
    url = default_storage.url(guardado)
    # MEDIA_URL del repo es "media/" (sin barra inicial); las plantillas y el
    # seed usan rutas con "/" inicial, así que se normaliza aquí.
    return url if url.startswith("/") else f"/{url}"
