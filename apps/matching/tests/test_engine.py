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


class CasosDocumentadosTests(SimpleTestCase):
    """
    Casos A-E de docs/DEVMATCH-MATCHING.md (sección 5), con la ponderación
    estándar v1.0. Si cambia la fórmula, hay que actualizar el documento y
    estos valores a la vez.
    """

    def _score(self, perfil, vacante):
        score, _ = calcular_match_score(perfil, vacante, PESOS)
        return score

    def test_caso_a_perfil_ideal(self):
        perfil = PerfilMatching({1, 2}, {10}, "avanzado", 5, 40)
        vacante = VacanteMatching({1, 2}, {10})
        self.assertAlmostEqual(self._score(perfil, vacante), 100.0, places=2)

    def test_caso_b_parcial(self):
        perfil = PerfilMatching({1}, {10}, "intermedio", 3, 20)
        vacante = VacanteMatching({1, 2}, {10, 11})
        score, factores = calcular_match_score(perfil, vacante, PESOS)
        self.assertAlmostEqual(score, 53.5, places=2)
        self.assertEqual(factores["habilidades"]["score"], 50.0)
        self.assertEqual(factores["tecnologias"]["score"], 50.0)
        self.assertEqual(factores["experiencia"]["score"], 60.0)
        self.assertEqual(factores["disponibilidad"]["score"], 50.0)

    def test_caso_c_sin_coincidencias_no_es_cero(self):
        perfil = PerfilMatching(set(), set(), "principiante", 0, 0)
        vacante = VacanteMatching({1}, {10})
        self.assertAlmostEqual(self._score(perfil, vacante), 5.0, places=2)

    def test_caso_d_vacante_sin_requisitos(self):
        perfil = PerfilMatching(set(), set(), "principiante", 0, 10)
        vacante = VacanteMatching()
        self.assertAlmostEqual(self._score(perfil, vacante), 72.5, places=2)

    def test_caso_e_topes_superados(self):
        perfil = PerfilMatching({1}, {10}, "avanzado", 12, 60)
        vacante = VacanteMatching({1}, {10})
        self.assertAlmostEqual(self._score(perfil, vacante), 100.0, places=2)