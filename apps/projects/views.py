from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView

from .forms import VacanteForm
from .models import Proyecto, ProyectoMedia


TABS = ("vacantes", "descripcion", "galeria")
TAB_INICIAL = "vacantes"

# Badge de estado de la cabecera: (clases de color, label). "Reclutando" es el
# único estado con semántica verde (spec); el resto usa violeta/neutral.
ESTADO_BADGE = {
    Proyecto.ESTADO_RECLUTANDO: "bg-green-100 text-green-700",
    Proyecto.ESTADO_FINALIZADO: "bg-green-100 text-green-700",
    Proyecto.ESTADO_BORRADOR: "bg-slate-100 text-slate-600",
    Proyecto.ESTADO_CANCELADO: "bg-slate-100 text-slate-600",
    Proyecto.ESTADO_PUBLICADO: "bg-violet-100 text-violet-700",
    Proyecto.ESTADO_EQUIPO_COMPLETO: "bg-violet-100 text-violet-700",
    Proyecto.ESTADO_EN_DESARROLLO: "bg-violet-100 text-violet-700",
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
        return Proyecto.objects.select_related("creador").filter(es_activo=True)

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