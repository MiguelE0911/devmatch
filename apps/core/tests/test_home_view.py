from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_responde_200(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_home_incluye_estado_de_bd(self):
        response = self.client.get(reverse("core:home"))
        self.assertIn("db_ok", response.context)