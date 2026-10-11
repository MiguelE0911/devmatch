from django.test import SimpleTestCase

from apps.matching.engine import PerfilMatching, VacanteMatching, calcular_match_score

PESOS = {
    "habilidades": 0.35,
    "nivel": 0.15,
    "tecnologias": 0.30,
    "experiencia": 0.10,
    "disponibilidad": 0.10,
}


class CalcularMatchScoreTests(SimpleTestCase):
    """
    SimpleTestCase (no TestCase): engine.py es Python puro, no toca la
    base de datos, así que estos tests corren sin --keepdb y en segundos.
    """

    def test_match_perfecto_da_100(self):
        perfil = PerfilMatching(
            habilidades_ids={1, 2},
            tecnologias_ids={10},
            nivel="avanzado",
            experiencia_anios=5,
            disponibilidad_horas_semana=40,
        )
        vacante = VacanteMatching(
            habilidades_requeridas_ids={1, 2}, tecnologias_requeridas_ids={10}
        )
        score, factores = calcular_match_score(perfil, vacante, PESOS)
        self.assertEqual(score, 100.0)
        self.assertEqual(factores["habilidades"]["score"], 100.0)
        self.assertEqual(factores["tecnologias"]["score"], 100.0)

    def test_sin_coincidencias_de_catalogo_da_cero_en_ese_factor(self):
        perfil = PerfilMatching(
            habilidades_ids=set(),
            tecnologias_ids=set(),
            nivel="principiante",
            experiencia_anios=0,
            disponibilidad_horas_semana=0,
        )
        vacante = VacanteMatching(
            habilidades_requeridas_ids={1}, tecnologias_requeridas_ids={10}
        )
        _, factores = calcular_match_score(perfil, vacante, PESOS)
        self.assertEqual(factores["habilidades"]["score"], 0.0)
        self.assertEqual(factores["tecnologias"]["score"], 0.0)

    def test_vacante_sin_requisitos_de_catalogo_da_score_completo(self):
        """Caso borde: si la vacante no pide habilidades/tecnologías
        específicas, no hay requisito que incumplir."""
        perfil = PerfilMatching(
            habilidades_ids=set(),
            tecnologias_ids=set(),
            nivel="principiante",
            experiencia_anios=0,
            disponibilidad_horas_semana=0,
        )
        vacante = VacanteMatching()  # sin requisitos
        _, factores = calcular_match_score(perfil, vacante, PESOS)
        self.assertEqual(factores["habilidades"]["score"], 100.0)
        self.assertEqual(factores["tecnologias"]["score"], 100.0)

    def test_nivel_avanzado_puntua_mas_que_principiante(self):
        base = dict(
            habilidades_ids=set(),
            tecnologias_ids=set(),
            experiencia_anios=0,
            disponibilidad_horas_semana=0,
        )
        vacante = VacanteMatching()
        _, f_principiante = calcular_match_score(
            PerfilMatching(nivel="principiante", **base), vacante, PESOS
        )
        _, f_avanzado = calcular_match_score(
            PerfilMatching(nivel="avanzado", **base), vacante, PESOS
        )
        self.assertGreater(
            f_avanzado["nivel"]["score"], f_principiante["nivel"]["score"]
        )

    def test_forma_del_json_coincide_con_devmatch_bd(self):
        perfil = PerfilMatching(
            habilidades_ids=set(),
            tecnologias_ids=set(),
            nivel="intermedio",
            experiencia_anios=2,
            disponibilidad_horas_semana=20,
        )
        vacante = VacanteMatching()
        _, factores = calcular_match_score(perfil, vacante, PESOS)
        for clave in ("habilidades", "nivel", "tecnologias", "experiencia", "disponibilidad"):
            self.assertIn(clave, factores)
            self.assertIn("score", factores[clave])
            self.assertIn("peso", factores[clave])