from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_responde_200(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_home_muestra_landing(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Arma el equipo")
        self.assertContains(response, "Cómo Funciona")
