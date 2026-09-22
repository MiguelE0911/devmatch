from django import forms

from apps.accounts.models import Habilidad, Tecnologia

from .models import Vacante, VacanteHabilidadRequerida, VacanteTecnologiaRequerida


class ChipCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Select múltiple renderizado como chips/pills lavanda (ver widget template)."""

    template_name = "widgets/chip_checkbox_select.html"


class VacanteForm(forms.ModelForm):
    """Formulario de alta de vacante.

    `habilidades` y `tecnologias` no son columnas de `vacantes` sino tablas
    puente (vacante_habilidades_requeridas / vacante_tecnologias_requeridas);
    se declaran como ModelMultipleChoiceField y `save()` sincroniza las filas
    puente (Etapa 1: alta. Edición futura reutiliza el mismo sync).
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

    class Meta:
        model = Vacante
        fields = [
            "titulo",
            "descripcion",
            "cupos_totales",
            "estado",
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
            "cupos_totales": forms.NumberInput(
                attrs={
                    "min": 1,
                    "class": "w-32 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
                }
            ),
            "estado": forms.Select(
                attrs={
                    "class": "w-48 appearance-none rounded-xl border border-slate-300 bg-white py-2.5 pl-9 pr-10 text-sm font-medium text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100",
                }
            ),
        }
        labels = {
            "titulo": "Título de la vacante",
            "descripcion": "Descripción de la vacante",
            "cupos_totales": "Cupos totales",
            "estado": "Estado de la vacante",
        }

    def save(self, commit=True):
        vacante = super().save(commit=commit)
        if commit:
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