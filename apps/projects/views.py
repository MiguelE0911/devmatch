import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView

from .forms import ProyectoForm, ProyectoMediaForm, VacanteForm
from .models import Proyecto, ProyectoMedia, Vacante
from .services import TRANSICIONES_VALIDAS


TABS = ("vacantes", "descripcion", "galeria")
TAB_INICIAL = "vacantes"

# Estados que NO se muestran a terceros en el detalle: "borrador" aún no es
# listable y "cancelado" no es un estado abierto (misma regla que el feed,
# core.views.ESTADOS_OCULTOS). El dueño del proyecto sí accede a los suyos —
# necesita ver/editar su borrador — por eso el filtro es "dueño OR visible".
ESTADOS_OCULTOS = (Proyecto.ESTADO_BORRADOR, Proyecto.ESTADO_CANCELADO)

# Badge de estado de la cabecera: (clases de color, label). Cada uno de los 7
# estados usa un color DIFERENTE (spec: "cada uno con un color diferente").
# `cancelado` NO se ofrece como opción editable: se le asigna automáticamente
# al dueño cuando intenta borrar el proyecto (lo aplica `ProyectoDeleteView`).
ESTADO_BADGE = {
    Proyecto.ESTADO_BORRADOR: "bg-slate-100 text-slate-600",
    Proyecto.ESTADO_PUBLICADO: "bg-violet-100 text-violet-700",
    Proyecto.ESTADO_RECLUTANDO: "bg-green-100 text-green-700",
    Proyecto.ESTADO_EQUIPO_COMPLETO: "bg-cyan-100 text-cyan-700",
    Proyecto.ESTADO_EN_DESARROLLO: "bg-amber-100 text-amber-700",
    Proyecto.ESTADO_FINALIZADO: "bg-emerald-100 text-emerald-700",
    Proyecto.ESTADO_CANCELADO: "bg-rose-100 text-rose-600",
}


def badge_estado(proyecto):
    return ESTADO_BADGE.get(proyecto.estado, "bg-violet-100 text-violet-700")


def _plural(n, singular, plural):
    return singular if n == 1 else plural


def hace_relativo(instante):
    """Fecha en una sola unidad: minutos → horas → días → semanas → meses → años.

    Preferencia de diseño: nunca mezclar dos unidades ("2 d y 4 h").
    """
    delta = timezone.now() - instante
    minutos = int(delta.total_seconds() // 60)
    if minutos < 60:
        if minutos < 1:
            return "hace un momento"
        return f"hace {minutos} {_plural(minutos, 'minuto', 'minutos')}"
    horas = minutos // 60
    if horas < 24:
        return f"hace {horas} {_plural(horas, 'hora', 'horas')}"
    dias = horas // 24
    if dias < 7:
        return f"hace {dias} {_plural(dias, 'día', 'días')}"
    semanas = dias // 7
    if semanas < 5:
        return f"hace {semanas} {_plural(semanas, 'semana', 'semanas')}"
    meses = dias // 30
    if meses < 12:
        return f"hace {meses} {_plural(meses, 'mes', 'meses')}"
    anios = dias // 365
    return f"hace {anios} {_plural(anios, 'año', 'años')}"


def datos_laterales(proyecto, usuario):
    """Datos compartidos por las tarjetas laterales (requisitos + equipo).

    `vacantes` con metadata (habilidades, tecnologías, cupos, slots) y el
    equipo derivado provisionalmente del cupo de cada vacante. Cuando exista
    `equipos_membresias` (Etapa 3) la "composición" se construye desde ahí.
    """
    es_dueno = usuario.is_authenticated and usuario.id == proyecto.creador_id
    vacantes = list(proyecto.vacantes.filter(es_activo=True).order_by("creado_en"))
    habilidades, tecnologias = [], []
    cupos_ocupados_total = cupos_totales_total = 0

    for vacante in vacantes:
        vacante.habilidades = [
            r.habilidad
            for r in vacante.vacantehabilidadrequerida_set.select_related(
                "habilidad"
            ).all()
        ]
        vacante.tecnologias = [
            r.tecnologia
            for r in vacante.vacantetecnologiarequerida_set.select_related(
                "tecnologia"
            ).all()
        ]
        vacante.cupos_libres = vacante.cupos_totales - vacante.cupos_ocupados
        # True = cupo libre (se pinta '?'), False = cupo ocupado (personaje).
        vacante.slots = [False] * vacante.cupos_ocupados + [True] * vacante.cupos_libres
        vacante.pct_ocupado = (
            round(vacante.cupos_ocupados / vacante.cupos_totales * 100)
            if vacante.cupos_totales
            else 0
        )
        # El botón "Postularme" se habilita solo si hay cupo, no es el dueño
        # y no está ya postulado (lo de "ya postulado" llega con el modelo de
        # postulaciones, Etapa 2). La vista Dueño lo mantiene deshabilitado.
        vacante.puede_postularse = (
            usuario.is_authenticated and not es_dueno and vacante.cupos_libres > 0
        )

        for habilidad in vacante.habilidades:
            if habilidad not in habilidades:
                habilidades.append(habilidad)
        for tecnologia in vacante.tecnologias:
            if tecnologia not in tecnologias:
                tecnologias.append(tecnologia)

        cupos_ocupados_total += vacante.cupos_ocupados
        cupos_totales_total += vacante.cupos_totales

    logo = (
        proyecto.media.filter(tipo=ProyectoMedia.TIPO_LOGO, es_activo=True)
        .order_by("orden")
        .first()
    )
    prototipos = list(
        proyecto.media.filter(tipo=ProyectoMedia.TIPO_PROTOTIPO, es_activo=True)
        .order_by("orden")
    )

    return {
        "vacantes": vacantes,
        "habilidades": habilidades,
        "tecnologias": tecnologias,
        "cupos_ocupados_total": cupos_ocupados_total,
        "cupos_totales_total": cupos_totales_total,
        "logo": logo,
        "prototipos": prototipos,
    }


class ProyectoDetailView(DetailView):
    """Detalle de un proyecto con 3 tabs (?tab=vacantes|descripcion|galeria)."""

    model = Proyecto
    template_name = "projects/project_detail.html"
    context_object_name = "proyecto"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        qs = Proyecto.objects.select_related("creador").filter(es_activo=True)
        usuario = self.request.user
        if not usuario.is_authenticated:
            return qs.exclude(estado__in=ESTADOS_OCULTOS)
        return qs.filter(Q(creador_id=usuario.id) | ~Q(estado__in=ESTADOS_OCULTOS))

    def get_object(self, queryset=None):
            proyecto = super().get_object(queryset)
            
            if proyecto.estado == Proyecto.ESTADO_BORRADOR and proyecto.creador_id != self.request.user.id:
                raise Http404("El proyecto no existe o aún es un borrador privado.")
                
            return proyecto
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        proyecto = self.object
        usuario = self.request.user

        tab = self.request.GET.get("tab", TAB_INICIAL)
        if tab not in TABS:
            tab = TAB_INICIAL
        ctx["tab"] = tab

        ctx["es_dueno"] = usuario.is_authenticated and usuario.id == proyecto.creador_id
        ctx["con_descripcion"] = True
        ctx["estado_badge"] = badge_estado(proyecto)
        ctx["publicado_hace"] = hace_relativo(proyecto.creado_en)
        ctx.update(datos_laterales(proyecto, usuario))
        return ctx


class VacancyCreateView(LoginRequiredMixin, CreateView):
    """Alta de vacante sobre un proyecto. Solo el creador del proyecto."""

    form_class = VacanteForm
    template_name = "projects/vacancy_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.proyecto = get_object_or_404(
            Proyecto.objects.filter(es_activo=True), pk=kwargs["pk"]
        )
        if request.user.id != self.proyecto.creador_id:
            messages.error(
                request, "Solo el creador del proyecto puede agregar vacantes."
            )
            return redirect("projects:project_detail", pk=self.proyecto.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proyecto"] = self.proyecto
        ctx["es_dueno"] = True
        ctx["estado_badge"] = badge_estado(self.proyecto)
        ctx.update(datos_laterales(self.proyecto, self.request.user))
        return ctx

    def form_valid(self, form):
        form.instance.proyecto = self.proyecto
        form.instance.es_activo = True
        return super().form_valid(form)

    def get_success_url(self):
        # El modelo Proyecto (Squad A) no define get_absolute_url; armamos la
        # URL aquí con reverse para no tocar models.py.
        return (
            reverse("projects:project_detail", kwargs={"pk": self.proyecto.pk})
            + "?tab=vacantes"
        )


class VacancyUpdateView(LoginRequiredMixin, UpdateView):
    """Edición de una vacante. Solo el creador (dueño) del proyecto.

    A diferencia del alta, aquí `estado` sí es editable ('abierta' /
    'cubierta' / 'cancelada'): cobertura y cancelación las gestiona el dueño;
    el trigger la mantiene en alta mientras el cupo esté vacante.
    """

    model = Vacante
    form_class = VacanteForm
    template_name = "projects/vacancy_form.html"
    context_object_name = "vacante"
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        vacante = get_object_or_404(
            Vacante.objects.select_related("proyecto__creador").filter(
                es_activo=True
            ),
            pk=kwargs["pk"],
        )
        if request.user.id != vacante.proyecto.creador_id:
            messages.error(
                request, "Solo el creador del proyecto puede editar la vacante."
            )
            return redirect(
                "projects:project_detail", pk=vacante.proyecto.pk
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Vacante.objects.select_related("proyecto__creador").filter(
            es_activo=True
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["include_estado"] = True
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proyecto"] = self.object.proyecto
        ctx["es_dueno"] = True
        ctx["estado_badge"] = badge_estado(self.object.proyecto)
        ctx.update(datos_laterales(self.object.proyecto, self.request.user))
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request, "Vacante actualizada correctamente."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return (
            reverse(
                "projects:project_detail",
                kwargs={"pk": self.object.proyecto.pk},
            )
            + "?tab=vacantes"
        )


class VacancyDeleteView(LoginRequiredMixin, View):
    """"Desactivar" una vacante: es_activo=False (no hay DELETE físico).

    Mismo contrato que ProyectoDeleteView: el trigger
    fn_prevenir_borrado_fisico bloquea el DELETE, así que se oculta
    conservando historial. Los cupos ocupados de la vacante se mantienen.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        vacante = get_object_or_404(
            Vacante.objects.select_related("proyecto__creador").filter(
                es_activo=True
            ),
            pk=pk,
        )
        proyecto = vacante.proyecto
        if request.user.id != proyecto.creador_id:
            messages.error(
                request, "Solo el creador del proyecto puede desactivar la vacante."
            )
            return redirect("projects:project_detail", pk=proyecto.pk)

        vacante.es_activo = False
        vacante.desactivado_en = timezone.now()
        vacante.desactivado_por = request.user
        vacante.save()

        messages.success(
            request, f"La vacante «{vacante.titulo}» se eliminó."
        )
        return redirect(
            reverse("projects:project_detail", kwargs={"pk": proyecto.pk})
            + "?tab=vacantes"
        )


class ProyectoGaleriaEditView(LoginRequiredMixin, CreateView):
    """Editor de la galería del proyecto (imágenes tipo `prototipo`).

    Espejo de `VacancyCreateView`: la página combina el form de alta de una
    imagen (por URL, sin Pillow todavía) con la lista de imágenes activas y su
    acción de desactivar. La "subida" es una URL en `archivo_url` (TEXT), igual
    que `logo_url` — el procesado con Pillow llega como valor agregado.
    """

    form_class = ProyectoMediaForm
    template_name = "projects/gallery_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.proyecto = get_object_or_404(
            Proyecto.objects.filter(es_activo=True), pk=kwargs["pk"]
        )
        if request.user.id != self.proyecto.creador_id:
            messages.error(
                request, "Solo el creador del proyecto puede editar la galería."
            )
            return redirect("projects:project_detail", pk=self.proyecto.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["proyecto"] = self.proyecto
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proyecto"] = self.proyecto
        ctx["es_dueno"] = True
        ctx["estado_badge"] = badge_estado(self.proyecto)
        ctx.update(datos_laterales(self.proyecto, self.request.user))
        return ctx

    def form_valid(self, form):
        form.instance.proyecto = self.proyecto
        form.instance.tipo = ProyectoMedia.TIPO_PROTOTIPO
        form.instance.es_activo = True
        messages.success(self.request, "La imagen se subió correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return (
            reverse("projects:project_detail", kwargs={"pk": self.proyecto.pk})
            + "?tab=galeria"
        )


class ProyectoMediaDeleteView(LoginRequiredMixin, View):
    """"Desactivar" una imagen de la galería: es_activo=False (no hay DELETE físico).

    Espejo de `VacancyDeleteView`. A diferencia de proyectos/vacantes,
    proyecto_media no tiene desactivado_en/desactivado_por_id (es un adjunto,
    ver DevMatch-BD, 5.2), así que basta con es_activo=False.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        media = get_object_or_404(
            ProyectoMedia.objects.select_related("proyecto__creador").filter(
                es_activo=True
            ),
            pk=pk,
        )
        proyecto = media.proyecto
        if request.user.id != proyecto.creador_id:
            messages.error(
                request, "Solo el creador del proyecto puede desactivar imágenes."
            )
            return redirect("projects:project_detail", pk=proyecto.pk)

        media.es_activo = False
        media.save()

        messages.success(
            request, "La imagen se eliminó de la galería."
        )
        return redirect(
            reverse("projects:project_detail", kwargs={"pk": proyecto.pk})
            + "?tab=galeria"
        )


class ProyectoMediaReorderView(LoginRequiredMixin, View):
    """Reordenar la galería (imágenes tipo `prototipo` activas) de un proyecto.

    Endpoint AJAX (POST JSON): recibe `{"ids": [...]}` con el orden completo de
    la galería y reetiqueta `orden` = índice para cada imagen dentro de un
    `transaction.atomic()`. La lista debe coincidir exactamente con las
    imágenes activas del proyecto; las desactivadas no participan y conservan
    su `orden`. Es un UPDATE normal, no aplica `fn_prevenir_borrado_fisico`.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        proyecto = get_object_or_404(
            Proyecto.objects.filter(es_activo=True), pk=pk
        )
        if request.user.id != proyecto.creador_id:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Solo el creador del proyecto puede reordenar la galería.",
                },
                status=403,
            )

        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

        ids = data.get("ids")
        if not isinstance(ids, list) or not ids:
            return JsonResponse(
                {"ok": False, "error": "Falta la lista de ids."}, status=400
            )

        activas = proyecto.media.filter(
            tipo=ProyectoMedia.TIPO_PROTOTIPO, es_activo=True
        )
        activas_ids = set(activas.values_list("pk", flat=True))
        if set(ids) != activas_ids:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "La lista no coincide con las imágenes activas.",
                },
                status=400,
            )

        with transaction.atomic():
            for posicion, media_id in enumerate(ids):
                activas.filter(pk=media_id).update(orden=posicion)
        return JsonResponse({"ok": True, "ids": ids})


class ProyectoEditView(LoginRequiredMixin, UpdateView):
    """Edición de los datos del proyecto. Solo el creador (dueño)."""

    model = Proyecto
    form_class = ProyectoForm
    template_name = "projects/project_form.html"
    pk_url_kwarg = "pk"
    context_object_name = "proyecto"

    def get_queryset(self):
        return Proyecto.objects.select_related("creador").filter(es_activo=True)

    def dispatch(self, request, *args, **kwargs):
        proyecto = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        if request.user.id != proyecto.creador_id:
            messages.error(request, "Solo el creador del proyecto puede editarlo.")
            return redirect("projects:project_detail", pk=proyecto.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["es_dueno"] = True
        ctx["estado_badge"] = badge_estado(self.object)
        ctx.update(datos_laterales(self.object, self.request.user))
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Proyecto actualizado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.object.pk})


class ProyectoDeleteView(LoginRequiredMixin, View):
    """"Desactivar" un proyecto: es_activo=False (no hay DELETE físico).

    Per contrato de honestidad del esquema v1, no existe estado 'archivado' ni
    borrado físico (trigger fn_prevenir_borrado_fisico). La acción es un UPDATE
    ortogonal: se oculta de la interfaz conservando su historial.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        proyecto = get_object_or_404(
            Proyecto.objects.filter(es_activo=True), pk=pk
        )
        if request.user.id != proyecto.creador_id:
            messages.error(
                request, "Solo el creador del proyecto puede desactivarlo."
            )
            return redirect("projects:project_detail", pk=proyecto.pk)

        if Proyecto.ESTADO_CANCELADO in TRANSICIONES_VALIDAS.get(proyecto.estado, set()):
            proyecto.estado = Proyecto.ESTADO_CANCELADO
            proyecto.cancelado_en = timezone.now()

        proyecto.es_activo = False
        proyecto.desactivado_en = timezone.now()
        proyecto.desactivado_por = request.user
        proyecto.save()

        # TODO audit: cuando exista apps/audit (services.py:log_action), registrar
        # "proyecto.desactivado" — DEVMATCH-BD 8.5 lo exige y nadie más lo loguea.
        messages.success(
            request, f"El proyecto «{proyecto.nombre}» se eliminó."
        )
        # No hay home interno todavía: el listado propio llega en una etapa posterior.
        return redirect("core:home")

class ProyectoCreateView(LoginRequiredMixin, CreateView):
    """Creación de un nuevo proyecto desde el modal."""

    model = Proyecto
    form_class = ProyectoForm
    template_name = "projects/project_create.html"

    def form_valid(self, form):
        form.instance.creador = self.request.user
        form.instance.es_activo = True
        messages.success(self.request, "¡Proyecto creado exitosamente!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.object.pk})