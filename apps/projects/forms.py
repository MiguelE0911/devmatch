from django import forms

from apps.accounts.models import Habilidad, Tecnologia

from .models import Proyecto, Vacante, VacanteHabilidadRequerida, VacanteTecnologiaRequerida


class InputClassesMixin:
    """Clases uniformes para los inputs del shell interno."""

    input_cls = (
        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 "
        "text-sm text-slate-900 placeholder-slate-400 focus:border-violet-500 "
        "focus:outline-none focus:ring-2 focus:ring-violet-100"
    )


class ProyectoForm(InputClassesMixin, forms.ModelForm):
    """Edición de los datos básicos del proyecto (solo el creador).

    `estado` no se edita aquí a propósito: las transiciones las valida el
    trigger `fn_validar_transicion_proyecto` y se gestionan aparte (toggle
    de estados válidos) para no chocar con la máquina de estados.
    `logo_url` y la galería viven en `proyecto_media`/`logo_url` (TEXT).
    """

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
                    "placeholder": "Contá de qué trata el proyecto...",
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


class ChipCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Select múltiple renderizado como chips/pills lavanda (ver widget template)."""

    template_name = "widgets/chip_checkbox_select.html"


class VacanteForm(forms.ModelForm):
    """Formulario de alta de vacante.

    `habilidades` y `tecnologias` no son columnas de `vacantes` sino tablas
    puente (vacante_habilidades_requeridas / vacante_tecnologias_requeridas);
    se declaran como ModelMultipleChoiceField y `save()` sincroniza las filas
    puente (Etapa 1: alta. Edición futura reutiliza el mismo sync).

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
        if commit:
            vacante.save()
            ids_habilidades = {h.pk for h in self.cleaned_data["habilidades"]}
            for bridge in vacante.vacantehabilidadrequerida_set.all():
                if bridge.habilidad_id not in ids_habilidades:
                    bridge.delete()
            for habilidad in self.cleaned_data["habilidades"]:
                VacanteHabilidadRequerida.objects.get_or_create(
                    vacante=vacante, habilidad=habilidad
                )

            ids_tecnologias = {t.pk for t in self.cleaned_data["tecnologias"]}
            for bridge in vacante.vacantetecnologiarequerida_set.all():
                if bridge.tecnologia_id not in ids_tecnologias:
                    bridge.delete()
            for tecnologia in self.cleaned_data["tecnologias"]:
                VacanteTecnologiaRequerida.objects.get_or_create(
                    vacante=vacante, tecnologia=tecnologia
                )
        return vacante