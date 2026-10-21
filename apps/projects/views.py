import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView, ListView
from apps.matching.engine import calcular_match_score
from apps.matching.models import ConfiguracionPesosMatching
from apps.applications.services import (
    construir_perfil_matching, 
    construir_vacante_matching,
    crear_postulacion, 
    PostulacionDuplicadaError, 
    ConfiguracionPesosNoDisponibleError, 
    VacanteNoPostulable, 
    VacanteSinCupo
)
from apps.applications.models import Postulacion

from .forms import ProyectoForm, ProyectoMediaForm, VacanteForm
from .models import Proyecto, ProyectoMedia, Vacante
from .services import (
    ESTADOS_CERRADOS,
    TRANSICIONES_VALIDAS,
    VacanteInvalida,
    cambiar_estado,
    puede_agregar_imagenes,
    puede_agregar_vacantes,
    esta_abierta,
    tiene_cupo_libre,
)


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


def url_volver(request, defecto):
    """Destino del botón "Volver".

    Prioriza un `?next=` interno (evita open redirect con
    `url_has_allowed_host_and_scheme`) y, si no hay o es externo, usa
    `defecto`. Reemplaza al viejo `history.back()`, que reabría pasos
    intermedios del historial (p. ej. el modal de creación).
    """
    candidato = request.GET.get("next", "")
    if candidato and url_has_allowed_host_and_scheme(
        candidato,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidato
    return defecto


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

    vacantes_postuladas_ids = set()
    if usuario.is_authenticated and not es_dueno:
        from apps.applications.models import Postulacion
        vacantes_postuladas_ids = set(
            Postulacion.objects.filter(
                vacante__proyecto=proyecto,
                postulante=usuario
            ).values_list("vacante_id", flat=True)
        )

    # Preparamos el perfil y los pesos una sola vez si el usuario puede ver el Match Score
    perfil_matching = None
    pesos = None
    if usuario.is_authenticated and not es_dueno:
        pesos_activos = ConfiguracionPesosMatching.objects.filter(es_activo=True).first()
        if pesos_activos:
            pesos = {
                "habilidades": float(pesos_activos.peso_habilidades),
                "nivel": float(pesos_activos.peso_nivel),
                "tecnologias": float(pesos_activos.peso_tecnologias),
                "experiencia": float(pesos_activos.peso_experiencia),
                "disponibilidad": float(pesos_activos.peso_disponibilidad),
            }
            perfil_matching = construir_perfil_matching(usuario)

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
        
        vacante.is_abierta = esta_abierta(vacante)
        vacante.tiene_cupo = tiene_cupo_libre(vacante)
        
        # Verificamos postulación y si el proyecto está RECLUTANDO
        ya_postulado = vacante.id in vacantes_postuladas_ids
        esta_reclutando = proyecto.estado == Proyecto.ESTADO_RECLUTANDO
        
        vacante.puede_postularse = (
            usuario.is_authenticated
            and not es_dueno
            and esta_reclutando
            and vacante.tiene_cupo
            and vacante.is_abierta
            and not ya_postulado
        )
        
        if not esta_reclutando:
            if proyecto.estado == Proyecto.ESTADO_PUBLICADO:
                vacante.motivo_no_postularse = "El reclutamiento aún no ha iniciado"
            else:
                vacante.motivo_no_postularse = "El proyecto ya no acepta postulaciones"
        elif es_dueno:
            vacante.motivo_no_postularse = "Eres el creador de este proyecto"
        elif not usuario.is_authenticated:
            vacante.motivo_no_postularse = "Inicia sesión para postularte"
        elif ya_postulado:
            vacante.motivo_no_postularse = "Ya te has postulado a esta vacante"
        else:
            vacante.motivo_no_postularse = "Publicación completa"

        # Calculamos y anexamos el Match Score dinámicamente a la vacante
        vacante.score_total = None
        vacante.factores = None
        if perfil_matching and pesos:
            vacante_matching = construir_vacante_matching(vacante)
            score_total, factores = calcular_match_score(perfil_matching, vacante_matching, pesos)
            vacante.score_total = score_total
            vacante.factores = factores

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
        # Un proyecto finalizado/cancelado ya no admite vacantes nuevas: la
        # tab de vacantes oculta el CTA "Añadir vacante" y VacancyCreateView
        # rechaza la URL directa (ver services.puede_agregar_vacantes).
        "puede_agregar_vacantes": puede_agregar_vacantes(proyecto),
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
        ctx["volver"] = url_volver(
            self.request, reverse("core:feed")
        )
        ctx.update(datos_laterales(proyecto, usuario))
        return ctx


class VacancyCreateView(LoginRequiredMixin, CreateView):
    """Alta de vacante sobre un proyecto. Solo el creador del proyecto.

    Solo se permite mientras el proyecto no esté cerrado (finalizado o
    cancelado) — ver `services.puede_agregar_vacantes`. El gate de navegación
    vive en `dispatch` y corta solo GET/HEAD: el POST llega siempre al
    formulario, que delega en `services.crear_vacante`; si el proyecto está
    cerrado el servicio lanza `ProyectoNoAceptaVacantes` y `form_valid` la
    muestra como error no de campo (200). El servicio es la fuente de verdad
    (regla del PR #10).
    """

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
            
        if request.method in ("GET", "HEAD") and not puede_agregar_vacantes(
            self.proyecto
        ):
            messages.error(
                request,
                "No se pueden gestionar vacantes en un proyecto en estado "
                f"«{self.proyecto.get_estado_display()}».",
            )
            return redirect(
                reverse(
                    "projects:project_detail", kwargs={"pk": self.proyecto.pk}
                )
                + "?tab=vacantes"
            )
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
        try:
            return super().form_valid(form)
        # Sumamos ValidationError a la captura de excepciones
        except (VacanteInvalida, ValidationError) as exc:
            # Regla de negocio del servicio (p. ej. proyecto finalizado o
            # cancelado, cupos, estado de vacante): se muestra como error no
            # de campo del formulario (200) y no se crea la vacante. El
            # servicio relee el proyecto con select_for_update dentro de su
            # transacción, así que no hace falta revalidar aquí.
            form.add_error(None, str(exc))
            return self.form_invalid(form)

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
            
        if not puede_agregar_vacantes(vacante.proyecto):
            messages.error(
                request, 
                "No se pueden editar vacantes en un proyecto en estado "
                f"«{vacante.proyecto.get_estado_display()}»."
            )
            return redirect("projects:project_detail", pk=vacante.proyecto.pk)
            
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
        try:
            response = super().form_valid(form)
        except (VacanteInvalida, ValidationError) as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(
            self.request, "Vacante actualizada correctamente."
        )
        return response

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

        if not puede_agregar_vacantes(proyecto):
            messages.error(
                request, 
                "No se pueden eliminar vacantes si el proyecto ya finalizó o se canceló."
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
    imagen (subida de archivo procesada con Pillow, o URL) con la lista de
    imágenes activas y su acción de desactivar. El valor final siempre queda
    en `archivo_url` (ruta relativa /media/... o URL externa).
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

    def post(self, request, *args, **kwargs):
        # Solo se bloquea el ALTA de imágenes (un proyecto cancelado no admite
        # nuevas capturas). El dueño puede seguir entrando a la página para
        # eliminar o reordenar las imágenes que ya existían.
        if not puede_agregar_imagenes(self.proyecto):
            messages.error(
                request,
                "No se pueden añadir imágenes a un proyecto en estado "
                f"«{self.proyecto.get_estado_display()}».",
            )
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

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
        ctx["puede_agregar_imagenes"] = puede_agregar_imagenes(self.proyecto)
        return ctx

    def form_valid(self, form):
        self.proyecto.refresh_from_db(fields=["estado"])
        if not puede_agregar_imagenes(self.proyecto):
            messages.error(
                self.request,
                "No se pueden añadir imágenes a un proyecto en estado "
                f"«{self.proyecto.get_estado_display()}».",
            )
            return redirect(self.get_success_url())
        form.instance.proyecto = self.proyecto
        form.instance.tipo = ProyectoMedia.TIPO_PROTOTIPO
        form.instance.es_activo = True
        try:
            with transaction.atomic():
                self.object = super().form_valid(form)
        except ValidationError as exc:
            # Fallo del storage al guardar la imagen (media_utils): la fila no
            # se crea y el formulario re-renderiza con el error.
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, "La imagen se subió correctamente.")
        return self.object

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
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, "Proyecto actualizado correctamente.")
        return response

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
            # Usar el servicio en lugar de asignar el estado a mano: además de
            # validar la transición y registrar cancelado_en, cierra las
            # vacantes que queden 'abiertas' (cerrar_vacantes_abiertas) —
            # revisión: un proyecto cancelado no puede seguir con vacantes
            # postulables.
            cambiar_estado(proyecto, Proyecto.ESTADO_CANCELADO)

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
    """Creación de un nuevo proyecto.

    Responde la página completa al acceso directo y el fragmento del modal
    (`_project_create_modal.html`) cuando la petición es AJAX
    (X-Requested-With), para que static/js/project-modal.js lo inyecte sin
    recargar. Un POST AJAX válido devuelve JSON con la URL de destino; uno
    inválido, el fragmento con los errores y status 422.
    """

    model = Proyecto
    form_class = ProyectoForm
    template_name = "projects/project_create.html"

    def _es_ajax(self):
        return self.request.headers.get("x-requested-with") == "XMLHttpRequest"

    def get_template_names(self):
        if self._es_ajax():
            return ["projects/_project_create_modal.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # La X / Cancelar del modal vuelven a la vista previa del shell
        # (?next llega desde parciales/sidebar) o al feed interno por defecto —
        # nunca a la landing. Solo se aceptan URLs internas (open redirect).
        # `volver_next` se re-emite en el action del form para que el modal
        # siga cerrándose bien tras un error de validación.
        next_url = self.request.GET.get("next", "")
        interno = bool(next_url) and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )
        ctx["volver"] = next_url if interno else reverse("core:feed")
        ctx["volver_next"] = next_url if interno else ""
        return ctx

    def form_valid(self, form):
        form.instance.creador = self.request.user
        form.instance.es_activo = True
        try:
            with transaction.atomic():
                self.object = form.save()
        except ValidationError as exc:
            # Fallo del storage al subir el logo: rollback (no queda proyecto
            # a medias) y el error como non-field error, sin duplicar al
            # reintentar.
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, "¡Proyecto creado exitosamente!")
        if self._es_ajax():
            return JsonResponse({"ok": True, "redirect": self.get_success_url()})
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self._es_ajax():
            response.status_code = 422
        return response

    def get_success_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.object.pk})

class MisProyectosListView(LoginRequiredMixin, ListView):
    model = Proyecto
    template_name = "projects/project_list.html"
    context_object_name = "proyectos"
    paginate_by = 6
    page_kwarg = "pagina"

    def get_queryset(self):
        return Proyecto.objects.filter(
            creador=self.request.user,
            es_activo=True
        ).prefetch_related(
            "media",
            "vacantes__vacantetecnologiarequerida_set__tecnologia",
            "vacantes__vacantehabilidadrequerida_set__habilidad",
        ).order_by("-creado_en")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        for proyecto in ctx["proyectos"]:
            proyecto.clases_badge = badge_estado(proyecto)
            proyecto.hace = hace_relativo(proyecto.creado_en)
            
            logos = getattr(proyecto, "logos_precargados", [])
            logo_obj = logos[0] if logos else None
            
            proyecto.url_logo = ""
            if logo_obj and getattr(logo_obj, "archivo_url", ""):
                proyecto.url_logo = logo_obj.archivo_url
            elif getattr(proyecto, "logo_url", ""):
                proyecto.url_logo = proyecto.logo_url

            vacantes_activas = [v for v in proyecto.vacantes.all() if getattr(v, 'es_activo', True)]
            proyecto.vacantes_list = vacantes_activas
            
            proyecto.cupos_ocupados_total = sum(getattr(v, 'cupos_ocupados', 0) for v in vacantes_activas)
            proyecto.cupos_totales_total = sum(getattr(v, 'cupos_totales', 0) for v in vacantes_activas)
            
            tecnologias_unicas = {}
            for vacante in vacantes_activas:
                if hasattr(vacante, 'vacantetecnologiarequerida_set'):
                    vacante.tech_list = [req.tecnologia for req in vacante.vacantetecnologiarequerida_set.all()]
                    for req in vacante.vacantetecnologiarequerida_set.all():
                        tecnologias_unicas[req.tecnologia.id] = req.tecnologia
                else:
                    vacante.tech_list = []
                    
                if hasattr(vacante, 'vacantehabilidadrequerida_set'):
                    vacante.hab_list = [req.habilidad for req in vacante.vacantehabilidadrequerida_set.all()]
                else:
                    vacante.hab_list = []

                postulaciones_list = []
                if hasattr(vacante, 'postulaciones'):
                    postulaciones_list = list(vacante.postulaciones.all())
                elif hasattr(vacante, 'postulacion_set'):
                    postulaciones_list = list(vacante.postulacion_set.all())

                for p in postulaciones_list:
                    if not hasattr(p, 'usuario') and hasattr(p, 'candidato'):
                        p.usuario = p.candidato
                    
                    p.score_total = float(p.match_score) if p.match_score is not None else 0
                    p.factores = p.match_factores

                preseleccionados = [
                    p for p in postulaciones_list 
                    if str(getattr(p, 'estado', '')).lower() in ['preseleccionado', 'preseleccionada', 'shortlisted']
                ]
                pendientes = [
                    p for p in postulaciones_list 
                    if str(getattr(p, 'estado', '')).lower() == 'pendiente'
                ]

                vacante.postulaciones_list = postulaciones_list
                vacante.postulaciones_preseleccionadas = preseleccionados
                vacante.postulaciones_pendientes = pendientes
                
                vacante.total_postulaciones = len(pendientes)
                vacante.total_preseleccionados = len(preseleccionados)
            
            proyecto.lista_tecnologias = list(tecnologias_unicas.values())

            nombre_limpio = proyecto.nombre.replace("—", " ").replace("-", " ").strip()
            palabras = [p for p in nombre_limpio.split() if p]
            if len(palabras) >= 2:
                proyecto.iniciales = (palabras[0][0] + palabras[1][0]).upper()
            elif len(palabras) == 1:
                proyecto.iniciales = palabras[0][:2].upper()
            else:
                proyecto.iniciales = "PR"

        if ctx.get("is_paginated"):
            paginator = ctx["paginator"]
            page_obj = ctx["page_obj"]
            rango_elidido = paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
            ctx["page_numbers"] = [str(x) if x != paginator.ELLIPSIS else "…" for x in rango_elidido]
            query_dict = self.request.GET.copy()
            if "pagina" in query_dict:
                del query_dict["pagina"]
            ctx["query_sin_pagina"] = query_dict.urlencode()
            
        return ctx


class PreseleccionarPostulacionView(LoginRequiredMixin, View):
    """Marca una postulación como preseleccionada."""
    http_method_names = ["post"]

    def post(self, request, pk):
        postulacion = get_object_or_404(Postulacion, pk=pk)
        proyecto = postulacion.vacante.proyecto
        
        if request.user.id != proyecto.creador_id:
            messages.error(request, "No tienes permisos para realizar esta acción.")
            return redirect("projects:mis_proyectos")

        postulacion.estado = Postulacion.ESTADO_PRESELECCIONADA 
        postulacion.save()

        candidato = postulacion.postulante
        nombre_usuario = getattr(candidato, "nombre", None) or getattr(candidato, "username", "Candidato")
        
        messages.success(request, f"¡Has preseleccionado a {nombre_usuario} para la vacante!")
        
        return redirect("projects:mis_proyectos")


class PostularseVacanteView(LoginRequiredMixin, View):
    """Procesa la postulación real de un usuario autenticado a una vacante."""
    http_method_names = ["post"]

    def post(self, request, pk):
        vacante = get_object_or_404(
            Vacante.objects.select_related("proyecto").filter(es_activo=True), 
            pk=pk
        )
        
        from apps.projects.models import Proyecto
        if vacante.proyecto.estado != Proyecto.ESTADO_RECLUTANDO:
            messages.error(request, "Solo puedes postularte a proyectos que estén en fase de reclutamiento.")
            return redirect("projects:project_detail", pk=vacante.proyecto.pk)
        
        if request.user.id == vacante.proyecto.creador_id:
            messages.error(request, "No puedes postularte a tu propio proyecto.")
            return redirect("projects:project_detail", pk=vacante.proyecto.pk)

        try:
            crear_postulacion(request.user, vacante)
            messages.success(request, "¡Te has postulado exitosamente a esta vacante! Tu compatibilidad ha sido registrada.")
        except PostulacionDuplicadaError:
            messages.error(request, "Ya tienes una postulación activa a esta vacante.")
        except (VacanteNoPostulable, VacanteSinCupo) as e:
            messages.error(request, str(e))
        except ConfiguracionPesosNoDisponibleError:
            messages.error(request, "El sistema de matching no está configurado temporalmente.")
        except ValidationError as e:
            messages.error(request, str(e.message) if hasattr(e, 'message') else str(e))
        except Exception:
            messages.error(request, "Ocurrió un error inesperado al procesar tu postulación.")

        return redirect(
            reverse("projects:project_detail", kwargs={"pk": vacante.proyecto.pk}) + "?tab=vacantes"
        )

class AprobarPostulacionView(LoginRequiredMixin, View):
    """Aprueba a un candidato preseleccionado y ocupa un cupo en la vacante."""
    http_method_names = ["post"]

    def post(self, request, pk):
        postulacion = get_object_or_404(Postulacion, pk=pk)
        vacante = postulacion.vacante
        proyecto = vacante.proyecto
        
        if request.user.id != proyecto.creador_id:
            messages.error(request, "No tienes permisos para realizar esta acción.")
            return redirect("projects:mis_proyectos")

        if vacante.cupos_ocupados >= vacante.cupos_totales:
            messages.error(request, "Esta vacante ya ha alcanzado su límite de cupos.")
        else:
            postulacion.estado = Postulacion.ESTADO_ACEPTADA
            postulacion.save()
            
            vacante.cupos_ocupados += 1
            vacante.save()

            candidato = postulacion.postulante
            nombre_usuario = getattr(candidato, "nombre", None) or getattr(candidato, "username", "Candidato")
            messages.success(request, f"¡Has aprobado a {nombre_usuario}! El cupo ha sido ocupado.")

        return redirect(
            reverse("projects:project_detail", kwargs={"pk": proyecto.pk}) + "?tab=vacantes"
        )

class RechazarPostulacionView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        from apps.applications.models import Postulacion
        postulacion = get_object_or_404(Postulacion, pk=pk)
        
        if request.user.id != postulacion.vacante.proyecto.creador_id:
            return JsonResponse({"error": "No autorizado"}, status=403)

        postulacion.estado = Postulacion.ESTADO_RECHAZADA
        postulacion.save()
        
        return JsonResponse({"ok": True})