"""
Motor de compatibilidad (CR-05). Python puro: recibe datos simples
(sets de ids, strings, números), no querysets ni instancias de modelo.
Esto permite probarlo sin tocar la base de datos (ver tests/test_engine.py,
SimpleTestCase, sin --keepdb necesario).

La forma del resultado (`factores`) coincide EXACTAMENTE con la documentada
en DEVMATCH-BD.md, sección 9 -- es el contrato que consume tanto
applications/services.py (snapshot al postular) como el dashboard visual
de Squad B. No cambiar los nombres de las llaves sin avisar a ambos lados.
"""

from dataclasses import dataclass, field

from apps.matching import constants


@dataclass
class PerfilMatching:
    habilidades_ids: set
    tecnologias_ids: set
    nivel: str
    experiencia_anios: int
    disponibilidad_horas_semana: int


@dataclass
class VacanteMatching:
    habilidades_requeridas_ids: set = field(default_factory=set)
    tecnologias_requeridas_ids: set = field(default_factory=set)


def _score_catalogo(poseidas: set, requeridas: set) -> float:
    """
    Porcentaje de los requisitos de la vacante que el perfil cubre.
    Si la vacante no pide nada de este catálogo, se considera cumplido
    al 100% (no hay requisito que incumplir).
    """
    if not requeridas:
        return 100.0
    coincidencias = len(poseidas & requeridas)
    return round((coincidencias / len(requeridas)) * 100, 2)


def _score_nivel(nivel: str) -> float:
    # SUPUESTO: ver nota en constants.py -- escala absoluta, no comparación
    # contra un requisito de la vacante (no existe esa columna en el esquema).
    orden = constants.NIVEL_ORDEN.get(nivel, 1)
    maximo = max(constants.NIVEL_ORDEN.values())
    return round((orden / maximo) * 100, 2)


def _score_experiencia(anios: int) -> float:
    # SUPUESTO: ver nota en constants.py.
    tope = constants.EXPERIENCIA_ANIOS_TOPE
    if tope <= 0:
        return 0.0
    return round(min(max(anios, 0), tope) / tope * 100, 2)


def _score_disponibilidad(horas: int) -> float:
    # SUPUESTO: ver nota en constants.py.
    tope = constants.DISPONIBILIDAD_HORAS_TOPE
    if tope <= 0:
        return 0.0
    return round(min(max(horas, 0), tope) / tope * 100, 2)


def calcular_match_score(
    perfil: PerfilMatching, vacante: VacanteMatching, pesos: dict
) -> tuple[float, dict]:
    """
    pesos: dict con las 5 llaves (habilidades, nivel, tecnologias,
    experiencia, disponibilidad) -> float. Deben sumar 1.000 (ya
    garantizado por el constraint chk_pesos_suman_uno de la BD, no se
    revalida aquí).

    Devuelve (score_total: float 0-100, factores: dict) con la forma:
    {
        "habilidades":    {"score": <0-100>, "peso": <float>},
        "nivel":          {"score": <0-100>, "peso": <float>},
        "tecnologias":    {"score": <0-100>, "peso": <float>},
        "experiencia":    {"score": <0-100>, "peso": <float>},
        "disponibilidad": {"score": <0-100>, "peso": <float>},
    }
    """
    factores = {
        "habilidades": {
            "score": _score_catalogo(
                perfil.habilidades_ids, vacante.habilidades_requeridas_ids
            ),
            "peso": pesos["habilidades"],
        },
        "nivel": {
            "score": _score_nivel(perfil.nivel),
            "peso": pesos["nivel"],
        },
        "tecnologias": {
            "score": _score_catalogo(
                perfil.tecnologias_ids, vacante.tecnologias_requeridas_ids
            ),
            "peso": pesos["tecnologias"],
        },
        "experiencia": {
            "score": _score_experiencia(perfil.experiencia_anios),
            "peso": pesos["experiencia"],
        },
        "disponibilidad": {
            "score": _score_disponibilidad(perfil.disponibilidad_horas_semana),
            "peso": pesos["disponibilidad"],
        },
    }

    score_total = sum(f["score"] * f["peso"] for f in factores.values())
    return round(score_total, 2), factores