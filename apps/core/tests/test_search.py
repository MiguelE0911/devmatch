from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Habilidad, Tecnologia
from apps.projects.models import (
    Proyecto,
    ProyectoMedia,
    Vacante,
    VacanteHabilidadRequerida,
    VacanteTecnologiaRequerida,
)

Usuario = get_user_model()


class BuscarProyectosViewTests(TestCase):
    """Autocompletado de la topbar (`core:buscar_proyectos`): JSON de solo
    lectura con las mismas reglas de visibilidad que el feed."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-buscar@devmatch.test", "creador-buscar", password="Clave-123!"
        )

    def _login(self):
        self.client.force_login(self.creador)

    def _proyecto(self, nombre, descripcion=None, estado=Proyecto.ESTADO_RECLUTANDO, **extra):
        return Proyecto.objects.create(
            creador=self.creador,
            nombre=nombre,
            descripcion=descripcion or f"Descripción de {nombre}",
            estado=estado,
            **extra,
        )

    def _vacante(self, proyecto, **extra):
        return Vacante.objects.create(
            proyecto=proyecto, titulo="Vacante", descripcion="d",
            cupos_totales=1, **extra,
        )

    def _resultados(self, resp):
        return resp.json()["resultados"]

    def test_requiere_login(self):
        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "abc"})
        self.assertEqual(resp.status_code, 302)

    def test_devuelve_json_con_campos_esperados(self):
        self._proyecto("Mercado Alpha")
        self._login()

        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "mercado"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")

        [item] = self._resultados(resp)
        self.assertEqual(
            sorted(item), ["estado", "id", "iniciales", "logo", "nombre", "url"]
        )
        self.assertEqual(item["nombre"], "Mercado Alpha")
        self.assertEqual(item["iniciales"], "MA")
        self.assertIsNone(item["logo"])

    def test_url_apunta_al_detalle_del_proyecto(self):
        proyecto = self._proyecto("Mercado Alpha")
        self._login()

        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "mercado"})
        [item] = self._resultados(resp)
        self.assertEqual(
            item["url"],
            reverse("projects:project_detail", kwargs={"pk": proyecto.pk}),
        )

    def test_usa_el_logo_cuando_existe(self):
        proyecto = self._proyecto("Con Logo")
        ProyectoMedia.objects.create(
            proyecto=proyecto,
            tipo=ProyectoMedia.TIPO_LOGO,
            archivo_url="/media/seed/logo.png",
            orden=0,
        )
        self._login()

        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "con lo"})
        [item] = self._resultados(resp)
        self.assertEqual(item["logo"], "/media/seed/logo.png")

    def test_busca_por_descripcion_y_por_requisitos(self):
        python = Tecnologia.objects.create(nombre="Python")
        liderazgo = Habilidad.objects.create(nombre="Liderazgo")
        proyecto = self._proyecto("Plataforma", descripcion="Gestiona inventarios")
        vacante = self._vacante(proyecto)
        VacanteTecnologiaRequerida.objects.create(vacante=vacante, tecnologia=python)
        VacanteHabilidadRequerida.objects.create(vacante=vacante, habilidad=liderazgo)
        self._login()

        def nombres(termino):
            resp = self.client.get(
                reverse("core:buscar_proyectos"), {"q": termino}
            )
            return [i["nombre"] for i in self._resultados(resp)]

        self.assertEqual(nombres("inventario"), ["Plataforma"])
        self.assertEqual(nombres("python"), ["Plataforma"])
        self.assertEqual(nombres("liderazgo"), ["Plataforma"])

    def test_termino_corto_o_vacio_no_devuelve_resultados(self):
        self._proyecto("Mercado Alpha")
        self._login()

        for termino in ("", "a"):
            resp = self.client.get(reverse("core:buscar_proyectos"), {"q": termino})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(self._resultados(resp), [])

    def test_omite_ocultos_y_desactivados(self):
        self._proyecto("Mercado Borrador", estado=Proyecto.ESTADO_BORRADOR)
        self._proyecto("Mercado Cancelado", estado=Proyecto.ESTADO_CANCELADO)
        self._proyecto("Mercado Borrado", es_activo=False)
        self._proyecto("Mercado Vivo")

        self._login()
        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "mercado"})
        self.assertEqual(
            [i["nombre"] for i in self._resultados(resp)], ["Mercado Vivo"]
        )

    def test_limita_la_cantidad_de_resultados(self):
        for i in range(10):
            self._proyecto(f"Mercado {i:02d}")
        self._login()

        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "mercado"})
        self.assertEqual(len(self._resultados(resp)), 6)

    def test_ordena_por_relevancia(self):
        self._proyecto("Portal Interno", descripcion="hecho con dev tools")
        self._proyecto("Reactor Dev")        # el nombre contiene "dev"
        self._proyecto("DevMatch Clone")     # el nombre empieza con "dev"
        self._login()

        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "dev"})
        self.assertEqual(
            [i["nombre"] for i in self._resultados(resp)],
            ["DevMatch Clone", "Reactor Dev", "Portal Interno"],
        )

    def test_prioriza_la_coincidencia_exacta_del_nombre(self):
        self._proyecto("Dev Team Alpha")     # empieza con "dev"
        self._proyecto("dev")                # coincide exactamente
        self._login()

        resp = self.client.get(reverse("core:buscar_proyectos"), {"q": "dev"})
        self.assertEqual(self._resultados(resp)[0]["nombre"], "dev")
