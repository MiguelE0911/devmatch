"""
CR-05 + CR-07: crea una postulación calculando el Match Score con el
motor de matching y congelándolo (snapshot) en match_factores en el
instante exacto en que el usuario aplica. Nunca se recalcula después
(CR-12: cambios de perfil posteriores no alteran postulaciones ya
registradas).
"""

from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.accounts.models import Perfil, UsuarioHabilidad, UsuarioTecnologia
from apps.matching.engine import PerfilMatching, VacanteMatching, calcular_match_score
from apps.matching.models import ConfiguracionPesosMatching
from apps.projects.models import VacanteHabilidadRequerida, VacanteTecnologiaRequerida

from .models import Postulacion

INDICE_POSTULACION_ACTIVA = "ux_postulacion_activa_unica"


class PostulacionDuplicadaError(Exception):
    """Ya existe una postulación pendiente/preseleccionada a esta vacante
    (ux_postulacion_activa_unica). Volver a postularse tras un rechazo o
    retiro SÍ está permitido -- solo se bloquea mientras hay una activa."""


class ConfiguracionPesosNoDisponibleError(Exception):
    """No hay una fila activa en configuracion_pesos_matching, así que no
    se puede calcular (ni explicar) el Match Score."""


def _construir_perfil_matching(usuario):
    # El Perfil NO se crea automáticamente al registrarse: las vistas de
    # accounts lo crean con get_or_create la primera vez que el usuario
    # entra a editarlo. Aquí se hace igual, para que un usuario que aún
    # no completó su perfil pueda postularse con los valores por defecto
    # (principiante, 0 años, 10 hrs/semana) en vez de romper.
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    habilidades_ids = set(
        UsuarioHabilidad.objects.filter(usuario=usuario).values_list(
            "habilidad_id", flat=True
        )
    )
    tecnologias_ids = set(
        UsuarioTecnologia.objects.filter(usuario=usuario).values_list(
            "tecnologia_id", flat=True
        )
    )
    return PerfilMatching(
        habilidades_ids=habilidades_ids,
        tecnologias_ids=tecnologias_ids,
        nivel=perfil.nivel,
        experiencia_anios=perfil.experiencia_anios,
        disponibilidad_horas_semana=perfil.disponibilidad_horas_semana,
    )


def _construir_vacante_matching(vacante):
    habilidades_ids = set(
        VacanteHabilidadRequerida.objects.filter(vacante=vacante).values_list(
            "habilidad_id", flat=True
        )
    )
    tecnologias_ids = set(
        VacanteTecnologiaRequerida.objects.filter(vacante=vacante).values_list(
            "tecnologia_id", flat=True
        )
    )
    return VacanteMatching(
        habilidades_requeridas_ids=habilidades_ids,
        tecnologias_requeridas_ids=tecnologias_ids,
    )


def crear_postulacion(usuario, vacante):
    """
    Devuelve la Postulacion creada.

    NO valida que la vacante esté abierta ni que el proyecto sea visible
    (no esté en borrador): esa regla corresponde a las vistas, según
    DEVMATCH-BD.md §7 y §9. Ver docs/DEVMATCH-MATCHING.md, sección 6.

    Levanta:
    - PostulacionDuplicadaError si el usuario ya tiene una postulación
      activa a esta vacante -- capturarla en la vista y mostrar el mensaje
      amigable correspondiente.
    - ConfiguracionPesosNoDisponibleError si no hay pesos activos en la BD.
    """
    try:
        pesos_activos = ConfiguracionPesosMatching.objects.get(es_activo=True)
    except ConfiguracionPesosMatching.DoesNotExist as exc:
        raise ConfiguracionPesosNoDisponibleError(
            "No hay una configuración de pesos activa en "
            "configuracion_pesos_matching; no se puede calcular el Match Score."
        ) from exc

    pesos = {
        "habilidades": float(pesos_activos.peso_habilidades),
        "nivel": float(pesos_activos.peso_nivel),
        "tecnologias": float(pesos_activos.peso_tecnologias),
        "experiencia": float(pesos_activos.peso_experiencia),
        "disponibilidad": float(pesos_activos.peso_disponibilidad),
    }

    perfil_matching = _construir_perfil_matching(usuario)
    vacante_matching = _construir_vacante_matching(vacante)
    score, factores = calcular_match_score(perfil_matching, vacante_matching, pesos)

    try:
        with transaction.atomic():
            return Postulacion.objects.create(
                vacante=vacante,
                postulante=usuario,
                match_score=Decimal(str(score)),
                match_factores=factores,
                pesos_usados=pesos_activos,
            )
    except IntegrityError as exc:
        # Solo se traduce el error del índice único parcial; cualquier otra
        # violación de integridad se deja pasar tal cual para no
        # disfrazarla de "postulación duplicada".
        if INDICE_POSTULACION_ACTIVA in str(exc):
            raise PostulacionDuplicadaError(
                "Ya tienes una postulación activa a esta vacante."
            ) from exc
        raise