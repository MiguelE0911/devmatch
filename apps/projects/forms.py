from django import forms
from django.utils import timezone

from apps.accounts.models import Habilidad, Tecnologia

from .models import Proyecto, ProyectoMedia, Vacante
from .media_utils import guardar_imagen, procesar_imagen
from .services import (
    ESTADOS_CERRADOS,
    TRANSICIONES_VALIDAS,
    actualizar_vacante,
    cerrar_vacantes_abiertas,
    crear_vacante,
)


class InputClassesMixin:
    """Clases uniformes para los inputs del shell interno."""

    input_cls = (
        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 "
        "text-sm text-slate-900 placeholder-slate-400 focus:border-violet-500 "
        "focus:outline-none focus:ring-2 focus:ring-violet-100"
    )

    archivo_cls = (
        "block w-full text-sm text-slate-600 file:mr-3 file:cursor-pointer "
        "file:rounded-full file:border-0 file:bg-violet-50 file:px-4 file:py-2 "
        "file:text-xs file:font-semibold file:text-violet-800 "
        "hover:file:bg-violet-100"
    )


class ProyectoForm(InputClassesMixin, forms.ModelForm):
    """Edición de los datos básicos del proyecto (solo el creador).

    `estado` se edita solo aquí, igual que la vacante en edición: el select
    ofrece únicamente el estado actual y las transiciones válidas según
    `services.TRANSICIONES_VALIDAS` (espejo del trigger
    `fn_validar_transicion_proyecto`). `clean_estado` valida como antemural
    para no depender del error crudo de Postgres; el trigger sigue siendo la
    garantía final. Al finalizar o cancelar se registran `finalizado_en` /
    `cancelado_en`, igual que hacen el servicio y el trigger.
    `logo_url` guarda la ruta relativa (/media/...) del archivo subido con
    Pillow o una URL externa pegada; `logo` (archivo) tiene prioridad y en
    `save()` escribe el resultado en `logo_url`. La galería vive en
    `proyecto_media` (tabla con columna TEXT `archivo_url`).
    """

    logo = forms.ImageField(
        label="Subir logo",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": InputClassesMixin.archivo_cls}
        ),
    )

    class Meta:
        model = Proyecto
        fields = ["nombre", "descripcion", "logo_url"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "placeholder": "Nombre del proyecto",
                    "class": InputClassesMixin.input_cls,
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Cuenta de qué trata el proyecto...",
                    "class": InputClassesMixin.input_cls,
                }
            ),
            "logo_url": forms.TextInput(
                attrs={
                    "placeholder": "https://...  (URL del logo, opcional)",
                    "class": InputClassesMixin.input_cls,
                }
            ),
        }
        labels = {
            "nombre": "Nombre del proyecto",
            "descripcion": "Descripción",
            "logo_url": "URL del logo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estado_original = (
            self.instance.estado if self.instance.pk else Proyecto.ESTADO_BORRADOR
        )
        permitidos = TRANSICIONES_VALIDAS.get(self._estado_original, set())
        # `cancelado` NO se ofrece como opción editable: es el estado que se le
        # asigna automáticamente al dueño cuando intenta borrar el proyecto
        # (lo aplica `ProyectoDeleteView`). Solo aparece en el select si ya es
        # el estado actual del proyecto (p. ej. al cancelar un borrado).
        opciones = ({self._estado_original} | permitidos) - {
            Proyecto.ESTADO_CANCELADO
        }
        if self._estado_original == Proyecto.ESTADO_CANCELADO:
            opciones.add(Proyecto.ESTADO_CANCELADO)
        if self.instance.pk:
            self.fields["estado"] = forms.ChoiceField(
                choices=[
                    (valor, etiqueta)
                    for valor, etiqueta in Proyecto.ESTADO_CHOICES
                    if valor in opciones
                ],
                initial=self._estado_original,
                label="Estado del proyecto",
                widget=forms.Select(
                    attrs={
                        "class": "w-64 appearance-none rounded-xl border border-slate-300 bg-white py-2.5 pl-9 pr-10 text-sm font-medium text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
                    }
                ),
            )

    def clean_estado(self):
        nuevo_estado = self.cleaned_data.get("estado")
        if not self.instance.pk or nuevo_estado == self._estado_original:
            return nuevo_estado
        if nuevo_estado not in TRANSICIONES_VALIDAS.get(self._estado_original, set()):
            etiquetas = dict(Proyecto.ESTADO_CHOICES)
            raise forms.ValidationError(
                f"No se puede pasar el proyecto de "
                f"'{etiquetas.get(self._estado_original)}' a "
                f"'{etiquetas.get(nuevo_estado)}'."
            )
        return nuevo_estado

    def clean_logo(self):
        """Valida y procesa el logo subido con Pillow (media_utils): peso,
        formato real y normalización. El ContentFile procesado queda en
        `cleaned_data["logo_procesado"]` y `save()` lo guarda en MEDIA_ROOT,
        escribiendo la URL resultante en `logo_url`.
        """
        logo = self.cleaned_data.get("logo")
        if logo:
            self.cleaned_data["logo_procesado"] = procesar_imagen(logo, "logo")
        return logo

    def save(self, commit=True):
        proyecto = super().save(commit=False)
        nuevo_estado = self.cleaned_data.get("estado")
        cambio_a_cerrado = False
        if nuevo_estado and nuevo_estado != self._estado_original:
            proyecto.estado = nuevo_estado
            if nuevo_estado == Proyecto.ESTADO_FINALIZADO:
                proyecto.finalizado_en = timezone.now()
            elif nuevo_estado == Proyecto.ESTADO_CANCELADO:
                proyecto.cancelado_en = timezone.now()
            cambio_a_cerrado = nuevo_estado in ESTADOS_CERRADOS
        if commit:
            proyecto.save()
            # El logo subido necesita el pk para guardar el archivo en
            # media/proyectos/<id>/, así que se guarda tras el proyecto.
            procesado = self.cleaned_data.get("logo_procesado")
            if procesado:
                proyecto.logo_url = guardar_imagen(proyecto.pk, "logo", procesado)
                proyecto.save()
            # Cerrar el ciclo (finalizado/cancelado) deja sin postulaciones a
            # las vacantes abiertas: misma regla que services.cambiar_estado.
            if cambio_a_cerrado:
                cerrar_vacantes_abiertas(proyecto)
        return proyecto


class ProyectoMediaForm(InputClassesMixin, forms.ModelForm):
    """Alta de una imagen de la galería (tipo `prototipo`).

    Espejo de `VacanteForm`. Formato híbrido: se puede SUBIR un archivo
    (procesado con Pillow en media_utils y guardado en MEDIA_ROOT) o pegar
    una URL externa; al menos uno de los dos es obligatorio. En ambos casos
    el valor final queda en la columna TEXT `archivo_url` del esquema (ruta
    relativa /media/... o URL externa), por eso el modelo no cambia.
    `orden` controla la posición en la galería; vacío = se agrega al final.
    `tipo` no se ofrece al usuario: el editor de galería es solo de
    prototipos.
    """

    archivo = forms.ImageField(
        label="Subir imagen",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": InputClassesMixin.archivo_cls}
        ),
    )

    archivo_url = forms.CharField(
        label="URL de la imagen",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "https://...  o /media/...  (URL de la captura)",
                "class": InputClassesMixin.input_cls,
            }
        ),
    )

    orden = forms.IntegerField(
        label="Orden (opcional)",
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "min": 0,
                "class": "w-32 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
            }
        ),
    )

    class Meta:
        model = ProyectoMedia
        fields = ["archivo_url", "orden"]

    def __init__(self, *args, proyecto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.proyecto = proyecto
        if proyecto is not None:
            self.fields["orden"].initial = self._siguiente_orden()

    def _siguiente_orden(self):
        ordenes = self.proyecto.media.filter(
            tipo=ProyectoMedia.TIPO_PROTOTIPO
        ).values_list("orden", flat=True)
        return (max(ordenes) if ordenes else -1) + 1

    def clean_archivo_url(self):
        url = (self.cleaned_data.get("archivo_url") or "").strip()
        if not url:
            return ""
        if not (
            url.startswith("http://")
            or url.startswith("https://")
            or url.startswith("/media/")
        ):
            raise forms.ValidationError(
                "La URL debe empezar con http(s):// o /media/ (ruta local)."
            )
        return url

    def clean_archivo(self):
        """Valida y procesa el archivo subido con Pillow (media_utils): peso,
        formato real y normalización. El ContentFile procesado queda en
        `cleaned_data["archivo_procesado"]` y `save()` lo guarda en
        MEDIA_ROOT, escribiendo la URL resultante en `archivo_url`.
        """
        archivo = self.cleaned_data.get("archivo")
        if archivo:
            self.cleaned_data["archivo_procesado"] = procesar_imagen(
                archivo, "prototipo"
            )
        return archivo

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("archivo") and not cleaned_data.get("archivo_url"):
            raise forms.ValidationError(
                "Sube una imagen o pegá su URL."
            )
        return cleaned_data

    def save(self, commit=True):
        media = super().save(commit=False)
        procesado = self.cleaned_data.get("archivo_procesado")
        if procesado:
            media.archivo_url = guardar_imagen(
                self.proyecto.pk, "prototipo", procesado
            )
        if media.orden is None:
            media.orden = self._siguiente_orden()
        if commit:
            media.save()
        return media


class ChipCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Select múltiple renderizado como chips/pills lavanda (ver widget template)."""

    template_name = "widgets/chip_checkbox_select.html"


class VacanteForm(forms.ModelForm):
    """Formulario de alta de vacante.

    `habilidades` y `tecnologias` no son columnas de `vacantes` sino tablas
    puente (vacante_habilidades_requeridas / vacante_tecnologias_requeridas);
    se declaran como ModelMultipleChoiceField; `save()` delega en
    services.crear_vacante / actualizar_vacante, que sincronizan las filas
    puente dentro de una transacción.

    `estado` NO es un campo del alta: toda vacante nace 'abierta' (los estados
    'cubierta'/'cancelada' los mantienen los triggers/una edición posterior,
    nunca el formulario de creación).
    `cupos_totales` se limita a 1..50 (decisión de equipo, margen amplio).
    """

    habilidades = forms.ModelMultipleChoiceField(
        queryset=Habilidad.objects.filter(es_activo=True).order_by("nombre"),
        widget=ChipCheckboxSelectMultiple,
        required=False,
        label="Habilidades requeridas",
    )
    tecnologias = forms.ModelMultipleChoiceField(
        queryset=Tecnologia.objects.filter(es_activo=True).order_by("nombre"),
        widget=ChipCheckboxSelectMultiple,
        required=False,
        label="Tecnologías requeridas",
    )

    cupos_totales = forms.IntegerField(
        label="Cupos totales",
        widget=forms.NumberInput(
            attrs={
                "min": 1,
                "max": 50,
                "class": "w-32 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
            }
        ),
    )

    class Meta:
        model = Vacante
        fields = [
            "titulo",
            "descripcion",
            "cupos_totales",
            "habilidades",
            "tecnologias",
        ]
        widgets = {
            "titulo": forms.TextInput(
                attrs={
                    "placeholder": "Desarrollador Frontend UI/UX",
                    "class": "w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Describe las responsabilidades del rol...",
                    "class": "w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
                }
            ),
        }
        labels = {
            "titulo": "Título de la vacante",
            "descripcion": "Descripción de la vacante",
        }

    def __init__(self, *args, include_estado=False, **kwargs):
        super().__init__(*args, **kwargs)
        # `habilidades`/`tecnologias` no son campos del modelo sino tablas
        # puente; Django no las precarga solo, así que las semilla desde las
        # filas puente actuales cuando editamos una vacante existente.
        if self.instance.pk:
            self.fields["habilidades"].initial = [
                bridge.habilidad_id
                for bridge in self.instance.vacantehabilidadrequerida_set.all()
            ]
            self.fields["tecnologias"].initial = [
                bridge.tecnologia_id
                for bridge in self.instance.vacantetecnologiarequerida_set.all()
            ]
        if include_estado:
            self.fields["estado"] = forms.ChoiceField(
                choices=Vacante.ESTADO_CHOICES,
                initial=(
                    self.instance.estado if self.instance.pk else Vacante.ESTADO_ABIERTA
                ),
                label="Estado de la vacante",
                widget=forms.Select(
                    attrs={
                        "class": "w-48 appearance-none rounded-xl border border-slate-300 bg-white py-2.5 pl-9 pr-10 text-sm font-medium text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
                    }
                ),
            )

    def clean_cupos_totales(self):
        cupos = self.cleaned_data.get("cupos_totales")
        if cupos is not None:
            if not (1 <= cupos <= 50):
                raise forms.ValidationError("Los cupos deben estar entre 1 y 50.")
            if self.instance.pk and cupos < (self.instance.cupos_ocupados or 0):
                raise forms.ValidationError(
                    "No se puede bajar a menos de los cupos ya ocupados "
                    f"({self.instance.cupos_ocupados})."
                )
        return cupos

    def save(self, commit=True):
        vacante = super().save(commit=False)
        # Toda vacante nace abierta; 'cubierta'/'cancelada' solo los gestionan
        # los triggers o la edición posterior (ver DevMatch-BD 6.2).
        if not self.instance.pk:
            vacante.estado = Vacante.ESTADO_ABIERTA
        if not commit:
            return vacante

        # Con commit=True las reglas de negocio y la sincronización de
        # requisitos viven en services.py, dentro de transaction.atomic().
        # Pueden levantar VacanteInvalida: la vista la captura y la muestra.
        datos = {
            "titulo": vacante.titulo,
            "descripcion": vacante.descripcion,
            "cupos_totales": vacante.cupos_totales,
            "habilidades": self.cleaned_data["habilidades"],
            "tecnologias": self.cleaned_data["tecnologias"],
        }
        if self.instance.pk:
            return actualizar_vacante(
                self.instance, estado=self.cleaned_data.get("estado"), **datos
            )
        return crear_vacante(self.instance.proyecto, **datos)