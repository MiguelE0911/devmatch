from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import OperationalError, connection
from django.db.models import Prefetch
from django.shortcuts import render
from django.views import View

from apps.accounts.models import Habilidad, Perfil, Tecnologia
from apps.projects.models import Proyecto, ProyectoMedia, Vacante
from apps.projects.views import hace_relativo


def home(request):
    """Landing page pública de DevMatch."""
    return render(request, "core/home.html")


def health(request):
    """Health-check de conexión a la base de datos."""
    db_ok = True
    db_error = None

    try:
        connection.ensure_connection()
    except OperationalError as exc:
        db_ok = False
        db_error = str(exc)

    db_settings = connection.settings_dict

    context = {
        "db_ok": db_ok,
        "db_error": db_error,

        # Información de la conexión PostgreSQL
        "db_engine": db_settings.get("ENGINE", "").rsplit(".", 1)[-1],
        "db_name": db_settings.get("NAME"),
        "db_user": db_settings.get("USER"),
        "db_host": db_settings.get("HOST") or "localhost",
        "db_port": db_settings.get("PORT") or "5432",
    }

    return render(request, "core/health.html", context)


# ---------------------------------------------------------------------------
# HOME INTERNO — feed de proyectos (post-login)
# ---------------------------------------------------------------------------
# Es el "Home" del sidebar: página protegida del shell que lista los
# proyectos visibles en cards de una sola columna, con paginación y filtros
# aplicados por query params (especificación visual "Home", sección 1).
# La landing pública sigue viviendo en `/` (core:home).

PROYECTOS_POR_PAGINA = 6

# Estados que nunca aparecen en el feed (borrador aún no listable, cancelado
# no es un estado abierto) y badges de los visibles. "Equipo completo" usa la
# escala índigo (spec home, §5): neutro pero no negativo, distinta del violeta
# de marca y del verde de "Reclutando". El detalle de proyecto mantiene su
# propio mapa (no se toca).
ESTADOS_OCULTOS = (Proyecto.ESTADO_BORRADOR, Proyecto.ESTADO_CANCELADO)
ESTADO_BADGE_FEED = {
    Proyecto.ESTADO_RECLUTANDO: "bg-green-100 text-green-700",
    Proyecto.ESTADO_FINALIZADO: "bg-green-100 text-green-700",
    Proyecto.ESTADO_PUBLICADO: "bg-violet-100 text-violet-700",
    Proyecto.ESTADO_EN_DESARROLLO: "bg-violet-100 text-violet-700",
    Proyecto.ESTADO_EQUIPO_COMPLETO: "bg-indigo-100 text-indigo-700",
}
BADGE_FEED_DEFECTO = "bg-violet-100 text-violet-700"

# Valores válidos para los filtros GET (validación estricta: un valor ajeno a
# los choices no rompe la página ni filtra por error).
ESTADOS_ESTADO_PROYECTO = {valor for valor, _ in Proyecto.ESTADO_CHOICES}
ESTADOS_VACANTE = {valor for valor, _ in Vacante.ESTADO_CHOICES}
NIVELES_PERFIL = {valor for valor, _ in Perfil.NIVEL_CHOICES}

# Vacantes activas de cada proyecto, con sus tecnologías/habilidades ya
# cargadas (mismo patrón de agregación que projects/views.datos_laterales,
# pero cacheado con Prefetch para el listado completo).
VACANTES_ACTIVAS = Prefetch(
    "vacantes",
    queryset=Vacante.objects.filter(es_activo=True).prefetch_related(
        "vacantetecnologiarequerida_set__tecnologia",
        "vacantehabilidadrequerida_set__habilidad",
    ),
    to_attr="_vacantes_activas",
)

# Logos: `proyecto_media` guarda el logo oficial (tipo 'logo') con su orden;
# la card lo muestra y, si no hay, cae a un monograma con las iniciales.
LOGOS_PROYECTO = Prefetch(
    "media",
    queryset=ProyectoMedia.objects.filter(
        tipo=ProyectoMedia.TIPO_LOGO
    ).order_by("orden", "pk"),
    to_attr="_logos",
)


def _ids_validos(parametros, nombre):
    """Convierte `?nombre=1&nombre=2` a una lista de ints, ignorando basura."""
    return [int(valor) for valor in parametros.getlist(nombre) if valor.isdigit()]


def _iniciales(nombre):
    """Monograma del proyecto (hasta 2 letras) para la miniatura sin logo."""
    palabras = [palabra for palabra in nombre.replace("–", " ").replace("—", " ").split()]
    if not palabras:
        return "DM"
    letras = palabras[0][0]
    if len(palabras) > 1:
        letras += palabras[1][0]
    return letras.upper()


def enriquecer_proyecto(proyecto):
    """Agrega a un `proyecto` el contexto que consume la card del feed.

    Se calcula sobre las vacantes activas ya prefetcheadas (atributo
    `_vacantes_activas`): cupos totales del proyecto, tecnologías distintivas
    ordenadas (la card muestra 3 + "…"), fecha relativa y badge de estado.
    """
    vacantes = getattr(proyecto, "_vacantes_activas", [])
    cupos_ocupados_total = cupos_totales_total = 0
    tecnologias, habilidades = [], []

    for vacante in vacantes:
        cupos_ocupados_total += vacante.cupos_ocupados
        cupos_totales_total += vacante.cupos_totales
        for puente in vacante.vacantetecnologiarequerida_set.all():
            tecnologia = puente.tecnologia
            if tecnologia not in tecnologias:
                tecnologias.append(tecnologia)
        for puente in vacante.vacantehabilidadrequerida_set.all():
            habilidad = puente.habilidad
            if habilidad not in habilidades:
                habilidades.append(habilidad)

    tecnologias.sort(key=lambda item: item.nombre.casefold())
    habilidades.sort(key=lambda item: item.nombre.casefold())

    proyecto.tecnologias = tecnologias
    proyecto.habilidades = habilidades
    proyecto.cupos_ocupados_total = cupos_ocupados_total
    proyecto.cupos_totales_total = cupos_totales_total
    proyecto.publicado_hace = hace_relativo(proyecto.creado_en)
    proyecto.badge = ESTADO_BADGE_FEED.get(proyecto.estado, BADGE_FEED_DEFECTO)
    # Miniatura: logo oficial (proyecto_media, tipo 'logo', por orden) y, si no
    # existe, un monograma con las iniciales del proyecto.
    logos = getattr(proyecto, "_logos", [])
    proyecto.logo = next(
        (logo.archivo_url for logo in logos if logo.archivo_url), None
    ) or proyecto.logo_url
    if not proyecto.logo:
        proyecto.iniciales = _iniciales(proyecto.nombre)
    return proyecto


class FeedView(LoginRequiredMixin, View):
    """Home interno (post-login): feed de proyectos + paginación + filtros GET.

    Filtros (todos opcionales, combinados con AND):
      ?habilidad=ID&tecnologia=ID     multi-selección sobre requisitos de vacantes activas
      ?nivel=principiante|intermedio|avanzado      sobre el perfil del creador
      ?experiencia=N                  mínimo de años de experiencia del creador
      ?estado_vacante=abierta|cubierta|cancelada   proyectos con ≥1 vacante activa en ese estado
      ?estado=reclutando|...          estado del proyecto (estados ocultos excluidos)
      ?pagina=N                       paginación
    """

    template_name = "core/feed.html"
    proyectos_por_pagina = PROYECTOS_POR_PAGINA

    def get(self, request):
        proyectos = (
            Proyecto.objects.filter(es_activo=True)
            .exclude(estado__in=ESTADOS_OCULTOS)
            .select_related("creador")
            .prefetch_related(VACANTES_ACTIVAS, LOGOS_PROYECTO)
            .order_by("-actualizado_en", "-pk")
        )

        estado = request.GET.get("estado")
        if estado and estado in ESTADOS_ESTADO_PROYECTO:
            proyectos = proyectos.filter(estado=estado)

        estado_vacante = request.GET.get("estado_vacante")
        if estado_vacante and estado_vacante in ESTADOS_VACANTE:
            proyectos = proyectos.filter(
                vacantes__estado=estado_vacante, vacantes__es_activo=True
            )

        habilidades_ids = _ids_validos(request.GET, "habilidad")
        for habilidad_id in habilidades_ids:
            proyectos = proyectos.filter(
                vacantes__vacantehabilidadrequerida__habilidad_id=habilidad_id,
                vacantes__es_activo=True,
            )

        tecnologias_ids = _ids_validos(request.GET, "tecnologia")
        for tecnologia_id in tecnologias_ids:
            proyectos = proyectos.filter(
                vacantes__vacantetecnologiarequerida__tecnologia_id=tecnologia_id,
                vacantes__es_activo=True,
            )

        nivel = request.GET.get("nivel")
        if nivel and nivel in NIVELES_PERFIL:
            proyectos = proyectos.filter(creador__perfil__nivel=nivel)

        experiencia = request.GET.get("experiencia")
        if experiencia and experiencia.isdigit():
            proyectos = proyectos.filter(
                creador__perfil__experiencia_anios__gte=int(experiencia)
            )

        proyectos = proyectos.distinct()

        paginator = Paginator(proyectos, self.proyectos_por_pagina)
        page_obj = paginator.get_page(request.GET.get("pagina"))

        for proyecto in page_obj.object_list:
            enriquecer_proyecto(proyecto)

        page_numbers = []
        if paginator.num_pages > 1:
            page_numbers = [
                "…" if pagina is Ellipsis else str(pagina)
                for pagina in paginator.get_elided_page_range(
                    page_obj.number, on_each_side=1, on_ends=1
                )
            ]

        query = request.GET.copy()
        query.pop("pagina", None)

        context = {
            "page_obj": page_obj,
            "proyectos": page_obj.object_list,
            "is_paginated": paginator.num_pages > 1,
            "page_numbers": page_numbers,
            "query_sin_pagina": query.urlencode(),
            # Opciones y estado de los filtros (los consume _filters_panel.html).
            "habilidades_catalogo": Habilidad.objects.filter(
                es_activo=True
            ).order_by("nombre"),
            "tecnologias_catalogo": Tecnologia.objects.filter(
                es_activo=True
            ).order_by("nombre"),
            "nivel_choices": Perfil.NIVEL_CHOICES,
            "estado_vacante_choices": Vacante.ESTADO_CHOICES,
            "estado_proyecto_choices": [
                choice
                for choice in Proyecto.ESTADO_CHOICES
                if choice[0] not in ESTADOS_OCULTOS
            ],
            "filtros": {
                "habilidades": set(habilidades_ids),
                "tecnologias": set(tecnologias_ids),
                "nivel": nivel,
                "experiencia": experiencia,
                "estado_vacante": estado_vacante,
                "estado": estado,
            },
        }
        return render(request, self.template_name, context)