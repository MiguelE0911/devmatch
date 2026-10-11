"""
Constantes del motor de matching (CR-05).

Pesos: CR-06 (que el Creador ajuste los pesos por vacante) está pospuesto,
así que los pesos son fijos. La fuente de verdad REAL es la tabla
configuracion_pesos_matching (ver ConfiguracionPesosMatching, es_activo=True)
-- engine.py recibe los pesos como parámetro, leídos de ahí por
applications/services.py. Los valores de aquí son solo un fallback/
referencia para tests que no tocan la base de datos, y deben coincidir
siempre con el registro sembrado en la BD (DevMatch-BD, sección 5.3:
0.35 / 0.15 / 0.30 / 0.10 / 0.10).
"""

PESOS_DEFAULT = {
    "habilidades": 0.35,
    "nivel": 0.15,
    "tecnologias": 0.30,
    "experiencia": 0.10,
    "disponibilidad": 0.10,
}

# --- Escalas para nivel / experiencia / disponibilidad ---------------------
# SUPUESTO (ver nota al equipo): Vacante no tiene columna de nivel mínimo,
# experiencia mínima ni disponibilidad requerida -- a diferencia de
# habilidades/tecnologías, que sí comparan contra un requisito real vía
# VacanteHabilidadRequerida/VacanteTecnologiaRequerida. Mientras no se
# confirme un criterio distinto con el equipo, estos tres factores se
# tratan como una escala absoluta de calidad del perfil del postulante,
# no como un "qué tan cerca estás del requisito de la vacante".

NIVEL_ORDEN = {
    "principiante": 1,
    "intermedio": 2,
    "avanzado": 3,
}

# A partir de esta cantidad de años, el factor "experiencia" llega a 100.
EXPERIENCIA_ANIOS_TOPE = 5

# A partir de esta cantidad de horas/semana, el factor "disponibilidad"
# llega a 100.
DISPONIBILIDAD_HORAS_TOPE = 40