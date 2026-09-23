from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView

from apps.projects.models import Proyecto
from apps.projects.views import badge_estado, hace_relativo
from apps.reviews.models import Resena

from .forms import ProfileEditForm, RegistroForm
from .models import (
    Habilidad,
    Interes,
    Perfil,
    Tecnologia,
    Usuario,
    UsuarioHabilidad,
    UsuarioInteres,
    UsuarioTecnologia,
)

# Categorías de la card "Habilidades": la vista y el formulario usan SIEMPRE
# los mismos nombres (el diseño pedía unificar "Backend Development"/"Backend"
# etc. en una sola convención). La agrupación es por palabra clave del nombre
# de la habilidad; las no reconocidas caen en "Herramientas".
GRUPOS_HABILIDADES = [
    ("Backend", ("Backend", "Database", "DevOps", "Data")),
    ("Frontend", ("Frontend", "UI/UX", "Mobile")),
]
GRUPO_DEFAULT = "Herramientas"


class RegistroView(CreateView):
    """Alta de cuenta pública. Al terminar redirige a login con un mensaje.

    Solo crea el Usuario (es_activo=True, es_admin=False por default del
    modelo). El Perfil técnico se completa después (profile_form).
    """

    model = Usuario
    form_class = RegistroForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "¡Cuenta creada! Iniciá sesión con tu correo para continuar.",
        )
        return response


def _grupo_de(habilidad):
    for grupo, claves in GRUPOS_HABILIDADES:
        if any(clave in habilidad.nombre for clave in claves):
            return grupo
    return GRUPO_DEFAULT


def _habilidades_del_usuario(usuario):
    ids = UsuarioHabilidad.objects.filter(usuario=usuario).values_list(
        "habilidad_id", flat=True
    )
    return Habilidad.objects.filter(id__in=ids, es_activo=True).order_by("nombre")


def _tecnologias_del_usuario(usuario):
    ids = UsuarioTecnologia.objects.filter(usuario=usuario).values_list(
        "tecnologia_id", flat=True
    )
    return Tecnologia.objects.filter(id__in=ids, es_activo=True).order_by("nombre")


def _intereses_del_usuario(usuario):
    ids = UsuarioInteres.objects.filter(usuario=usuario).values_list(
        "interes_id", flat=True
    )
    return Interes.objects.filter(id__in=ids, es_activo=True).order_by("nombre")


def agrupar_habilidades(usuario):
    """Devuelve [{grupo, habilidades: [...]}...] solo con los grupos que tengan
    chips, para la card "Habilidades" de la vista de perfil."""
    agrupadas = {}
    for habilidad in _habilidades_del_usuario(usuario):
        agrupadas.setdefault(_grupo_de(habilidad), []).append(habilidad)
    return [
        {"grupo": grupo, "habilidades": agrupadas[grupo]}
        for grupo in agrupadas
    ]


class ProfileDetailView(LoginRequiredMixin, TemplateView):
    """Vista de perfil técnico (solo lectura). Como buena práctica no se
    inventa nada: las reseñas son las que otros miembros le hicieron al
    usuario (Resena.destinatario), y los proyectos los que él creó."""

    template_name = "accounts/profile_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.request.user
        perfil, _ = Perfil.objects.get_or_create(usuario=usuario)

        ctx["usuario"] = usuario
        ctx["perfil"] = perfil
        ctx["grupos_habilidades"] = agrupar_habilidades(usuario)
        ctx["tecnologias"] = _tecnologias_del_usuario(usuario)
        ctx["intereses"] = _intereses_del_usuario(usuario)
        ctx["proyectos"] = (
            Proyecto.objects.filter(creador=usuario, es_activo=True)
            .order_by("-actualizado_en", "-creado_en")
        )
        for proyecto in ctx["proyectos"]:
            proyecto.estado_badge = badge_estado(proyecto)
        resenas = (
            Resena.objects.filter(destinatario=usuario, es_activo=True)
            .select_related("autor")
            .order_by("-creado_en")
        )
        for resena in resenas:
            resena.creado_hace = hace_relativo(resena.creado_en)
        ctx["resenas"] = resenas
        ctx["resenas_count"] = resenas.count()
        return ctx


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edición de perfil técnico. Actualiza Usuario + Perfil y sincroniza las
    tablas puente de habilidades/tecnologías/intereses."""

    model = Perfil
    form_class = ProfileEditForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return Perfil.objects.get_or_create(usuario=self.request.user)[0]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx.get("form")
        # Agrupación con estado "checked" para pintar los chips del editor:
        # recorre TODO el catálogo activo y marca lo que trae el formulario
        # (POST) o lo que ya tiene el usuario (GET).
        if form is None:
            return ctx
        ctx["grupos_habilidades"] = self._grupos_para_editor(
            Habilidad, "habilidades", form, _grupo_de
        )
        ctx["opciones_tecnologias"] = self._opciones_para_editor(
            Tecnologia, "tecnologias", form
        )
        ctx["opciones_intereses"] = self._opciones_para_editor(
            Interes, "intereses", form
        )
        return ctx

    def _seleccionados(self, form, campo):
        if form.data:
            return {int(pk) for pk in form.data.getlist(campo) if pk}
        return set(form.initial.get(campo, [])) if getattr(form, "initial", None) else set()

    def _grupos_para_editor(self, modelo, campo, form, agrupador):
        seleccionados = self._seleccionados(form, campo)
        agrupadas = {}
        for item in modelo.objects.filter(es_activo=True).order_by("nombre"):
            agrupadas.setdefault(agrupador(item), []).append(
                {"item": item, "checked": item.pk in seleccionados}
            )
        return [
            {"grupo": grupo, "items": agrupadas[grupo]} for grupo in agrupadas
        ]

    def _opciones_para_editor(self, modelo, campo, form):
        seleccionados = self._seleccionados(form, campo)
        return [
            {"item": item, "checked": item.pk in seleccionados}
            for item in modelo.objects.filter(es_activo=True).order_by("nombre")
        ]

    def form_valid(self, form):
        # Sincroniza las tres tablas puente: DELETE de lo deseleccionado e
        # INSERT de lo nuevo (los puentes sí permiten borrado físico, no así
        # los catálogos — ver docs/DEVMATCH-BD.md).
        habilidades_previas = set(
            UsuarioHabilidad.objects.filter(usuario=self.request.user).values_list(
                "habilidad_id", flat=True
            )
        )
        tecnologias_previas = set(
            UsuarioTecnologia.objects.filter(usuario=self.request.user).values_list(
                "tecnologia_id", flat=True
            )
        )
        intereses_previos = set(
            UsuarioInteres.objects.filter(usuario=self.request.user).values_list(
                "interes_id", flat=True
            )
        )

        response = super().form_valid(form)

        habilidades_nuevas = {h.pk for h in form.cleaned_data["habilidades"]}
        tecnologias_nuevas = {t.pk for t in form.cleaned_data["tecnologias"]}
        intereses_nuevos = {i.pk for i in form.cleaned_data["intereses"]}

        UsuarioHabilidad.objects.filter(
            usuario=self.request.user, habilidad_id__in=habilidades_previas - habilidades_nuevas
        ).delete()
        for pk in habilidades_nuevas - habilidades_previas:
            UsuarioHabilidad.objects.get_or_create(
                usuario=self.request.user, habilidad_id=pk
            )

        UsuarioTecnologia.objects.filter(
            usuario=self.request.user, tecnologia_id__in=tecnologias_previas - tecnologias_nuevas
        ).delete()
        for pk in tecnologias_nuevas - tecnologias_previas:
            UsuarioTecnologia.objects.get_or_create(
                usuario=self.request.user, tecnologia_id=pk
            )

        UsuarioInteres.objects.filter(
            usuario=self.request.user, interes_id__in=intereses_previos - intereses_nuevos
        ).delete()
        for pk in intereses_nuevos - intereses_previos:
            UsuarioInteres.objects.get_or_create(usuario=self.request.user, interes_id=pk)

        messages.success(self.request, "Tu perfil se guardó correctamente.")
        return response