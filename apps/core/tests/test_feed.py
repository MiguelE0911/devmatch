from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Habilidad, Perfil, Tecnologia
from apps.projects.models import (
    Proyecto,
    ProyectoMedia,
    Vacante,
    VacanteHabilidadRequerida,
    VacanteTecnologiaRequerida,
)

Usuario = get_user_model()


class FeedViewTests(TestCase):
    """Home interno (`core:feed`, /home/): feed de proyectos del spec Home."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-feed@devmatch.test", "creador-feed", password="Clave-123!"
        )
        self.creador.first_name = "Ana"
        self.creador.last_name = "Gómez"
        self.creador.save()

    def _crear_proyecto(self, nombre, estado=Proyecto.ESTADO_PUBLICADO, **extra):
        return Proyecto.objects.create(
            creador=self.creador,
            nombre=nombre,
            descripcion=f"Descripción de {nombre}",
            estado=estado,
            **extra,
        )

    def _login(self):
        self.client.force_login(self.creador)

    # -- Acceso -------------------------------------------------------------

    def test_feed_requiere_login(self):
        resp = self.client.get(reverse("core:feed"))
        self.assertEqual(resp.status_code, 302)

    def test_feed_usa_la_plantilla_correcta(self):
        self._crear_proyecto("Red Social")
        self._login()
        resp = self.client.get(reverse("core:feed"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "core/feed.html")

    def test_feed_incluye_panel_de_filtros(self):
        self._crear_proyecto("Red Social")
        self._login()
        resp = self.client.get(reverse("core:feed"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="panel-filtros"')
        self.assertContains(resp, "data-filters-toggle")
        for etiqueta in ("Habilidades", "Tecnologías", "Nivel", "Experiencia",
                         "Estado de vacante", "Estado del proyecto"):
            self.assertContains(resp, etiqueta)

    # -- Visibilidad --------------------------------------------------------

    def test_feed_muestra_proyectos_visibles_y_oculta_borradores(self):
        self._crear_proyecto("Proyecto Visible", estado=Proyecto.ESTADO_RECLUTANDO)
        self._crear_proyecto("En Borrador", estado=Proyecto.ESTADO_BORRADOR)
        self._crear_proyecto("Cancelado", estado=Proyecto.ESTADO_CANCELADO)
        self._login()
        resp = self.client.get(reverse("core:feed"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Proyecto Visible")
        self.assertNotContains(resp, "En Borrador")
        self.assertNotContains(resp, "Cancelado")

    def test_feed_oculta_proyectos_desactivados(self):
        self._crear_proyecto("Eliminado", es_activo=False)
        self._login()
        resp = self.client.get(reverse("core:feed"))
        self.assertNotContains(resp, "Eliminado")

    # -- Contexto de la card -------------------------------------------------

    def test_feed_agrega_metadatos_a_la_card(self):
        proyecto = self._crear_proyecto("Plataforma A")
        vacante = Vacante.objects.create(
            proyecto=proyecto,
            titulo="Backend",
            descripcion="API",
            cupos_totales=2,
            cupos_ocupados=1,
        )
        python = Tecnologia.objects.create(nombre="Python")
        django = Tecnologia.objects.create(nombre="Django")
        VacanteTecnologiaRequerida.objects.create(vacante=vacante, tecnologia=python)
        VacanteTecnologiaRequerida.objects.create(vacante=vacante, tecnologia=django)

        self._login()
        resp = self.client.get(reverse("core:feed"))

        card = resp.context["proyectos"][0]
        self.assertEqual(card, proyecto)
        self.assertEqual(card.cupos_ocupados_total, 1)
        self.assertEqual(card.cupos_totales_total, 2)
        self.assertEqual([t.nombre for t in card.tecnologias], ["Django", "Python"])
        self.assertTrue(card.publicado_hace)
        self.assertTrue(card.badge)

    def test_feed_dibuja_pills_e_importante_no_pillar_todas(self):
        proyecto = self._crear_proyecto("Con mucha Stack")
        vacante = Vacante.objects.create(
            proyecto=proyecto,
            titulo="Fullstack",
            descripcion="Todo",
            cupos_totales=4,
        )
        nombres = ["A1", "A2", "A3", "A4", "B1"]
        for nombre in nombres:
            tecnologia = Tecnologia.objects.create(nombre=nombre)
            VacanteTecnologiaRequerida.objects.create(vacante=vacante, tecnologia=tecnologia)

        self._login()
        resp = self.client.get(reverse("core:feed"))
        self.assertEqual(resp.status_code, 200)
        # Las 3 primeras se muestran como pill; el resto se resume con "…".
        self.assertContains(resp, "A1")
        self.assertContains(resp, "…")

    # -- Paginación ----------------------------------------------------------

    def test_feed_pagina_proyectos_con_tamano_esperado(self):
        for i in range(13):
            self._crear_proyecto(f"Proyecto {i:02d}")
        self._login()
        resp = self.client.get(reverse("core:feed"))

        self.assertEqual(resp.context["page_obj"].paginator.num_pages, 3)
        self.assertEqual(len(resp.context["page_obj"].object_list), 6)
        self.assertContains(resp, "Paginación del feed")
        self.assertContains(resp, "Atrás")
        self.assertContains(resp, "Siguiente")
        self.assertContains(resp, "2")

        tercera = self.client.get(reverse("core:feed"), {"pagina": "3"})
        self.assertEqual(tercera.status_code, 200)
        self.assertEqual(len(tercera.context["page_obj"].object_list), 1)
        self.assertEqual(tercera.context["page_obj"].paginator.num_pages, 3)

    def test_feed_pagina_fuera_de_rango_vuelve_a_la_ultima(self):
        for i in range(3):
            self._crear_proyecto(f"Proyecto {i}")
        self._login()
        resp = self.client.get(reverse("core:feed"), {"pagina": "999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["page_obj"].number, 1)

    def test_card_usa_logo_real_cuando_existe(self):
        proyecto = self._crear_proyecto("Con Logo")
        ProyectoMedia.objects.create(
            proyecto=proyecto,
            tipo=ProyectoMedia.TIPO_LOGO,
            archivo_url="/media/seed/logo.png",
            orden=0,
        )
        self._login()
        resp = self.client.get(reverse("core:feed"))
        card = resp.context["proyectos"][0]
        self.assertEqual(card.logo, "/media/seed/logo.png")
        self.assertContains(resp, 'src="/media/seed/logo.png"')

    def test_card_muestra_monograma_cuando_no_hay_logo(self):
        self._crear_proyecto("Alpha Beta")
        self._login()
        resp = self.client.get(reverse("core:feed"))
        card = resp.context["proyectos"][0]
        self.assertEqual(card.iniciales, "AB")
        self.assertContains(resp, ">AB<")

    def test_feed_pagina_no_numerica_cae_en_la_primera(self):
        self._crear_proyecto("Proyecto A")
        self._login()
        resp = self.client.get(reverse("core:feed"), {"pagina": "abc"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["page_obj"].number, 1)

    # -- Vacante inactiva no aporta cupos ni tecnologías ----------------------

    def test_feed_ignora_vacantes_inactivas(self):
        proyecto = self._crear_proyecto("Solo Activas")
        inactiva = Vacante.objects.create(
            proyecto=proyecto,
            titulo="Cerrada",
            descripcion="Cerrada",
            cupos_totales=3,
            es_activo=False,
        )
        tecnologia = Tecnologia.objects.create(nombre="Go")
        VacanteTecnologiaRequerida.objects.create(vacante=inactiva, tecnologia=tecnologia)

        self._login()
        resp = self.client.get(reverse("core:feed"))
        card = resp.context["proyectos"][0]
        self.assertEqual(card.cupos_totales_total, 0)
        self.assertEqual(card.tecnologias, [])


class FeedFilterViewTests(TestCase):
    """Filtros del feed (spec Home, §2-§6): se aplican por query param (GET),
    combinados con AND y sobre las vacantes activas."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-filtros@devmatch.test", "creador-filtros", password="Clave-123!"
        )
        self.otro = Usuario.objects.create_user(
            "creador-filtros-2@devmatch.test", "creador-filtros-2", password="Clave-123!"
        )

    def _login(self):
        self.client.force_login(self.creador)

    def _proyecto(self, nombre, creador=None, estado=Proyecto.ESTADO_RECLUTANDO):
        return Proyecto.objects.create(
            creador=creador or self.creador,
            nombre=nombre,
            descripcion=f"Descripción de {nombre}",
            estado=estado,
        )

    def _vacante(self, proyecto, estado=Vacante.ESTADO_ABIERTA, cupos=2, **extra):
        return Vacante.objects.create(
            proyecto=proyecto, titulo="Vacante", descripcion="d", estado=estado,
            cupos_totales=cupos, **extra,
        )

    def _nombres(self, resp):
        return [p.nombre for p in resp.context["proyectos"]]

    # -- Habilidades / tecnologías (multiselect) -----------------------------

    def test_filtro_por_habilidad(self):
        django = Habilidad.objects.create(nombre="Django")
        vacante = self._vacante(self._proyecto("Con Django"))
        VacanteHabilidadRequerida.objects.create(vacante=vacante, habilidad=django)
        self._proyecto("Sin Django")

        self._login()
        resp = self.client.get(reverse("core:feed"), {"habilidad": django.pk})
        self.assertEqual(self._nombres(resp), ["Con Django"])

    def test_filtro_por_varias_habilidades_es_and(self):
        a = Habilidad.objects.create(nombre="Habilidad A")
        b = Habilidad.objects.create(nombre="Habilidad B")
        proyecto_ab = self._proyecto("Ambas")
        vacante_ab = self._vacante(proyecto_ab)
        VacanteHabilidadRequerida.objects.create(vacante=vacante_ab, habilidad=a)
        VacanteHabilidadRequerida.objects.create(vacante=vacante_ab, habilidad=b)
        proyecto_solo_a = self._proyecto("Solo A")
        vacante_a = self._vacante(proyecto_solo_a)
        VacanteHabilidadRequerida.objects.create(vacante=vacante_a, habilidad=a)

        self._login()
        resp = self.client.get(
            reverse("core:feed"), {"habilidad": [a.pk, b.pk]}
        )
        self.assertEqual(self._nombres(resp), ["Ambas"])

    def test_panel_refleja_el_estado_seleccionado(self):
        python = Habilidad.objects.create(nombre="Python")
        vacante = self._vacante(self._proyecto("Con Python"))
        VacanteHabilidadRequerida.objects.create(vacante=vacante, habilidad=python)

        self._login()
        resp = self.client.get(reverse("core:feed"), {"habilidad": python.pk})
        self.assertEqual(resp.context["filtros"]["habilidades"], {python.pk})
        self.assertContains(
            resp,
            f'<input type="hidden" name="habilidad" value="{python.pk}">',
        )

    def test_filtro_por_tecnologia(self):
        python = Tecnologia.objects.create(nombre="Python")
        go = Tecnologia.objects.create(nombre="Go")
        vacante = self._vacante(self._proyecto("Con Python"))
        VacanteTecnologiaRequerida.objects.create(vacante=vacante, tecnologia=python)
        self._proyecto("Con Go")  # sin puente requerido

        self._login()
        resp = self.client.get(reverse("core:feed"), {"tecnologia": python.pk})
        self.assertEqual(self._nombres(resp), ["Con Python"])

    def test_filtro_ignora_vacantes_inactivas(self):
        python = Habilidad.objects.create(nombre="Python")
        proyecto_inactivo = self._proyecto("Vacante Inactiva")
        vacante = self._vacante(proyecto_inactivo, es_activo=False)
        VacanteHabilidadRequerida.objects.create(vacante=vacante, habilidad=python)

        self._login()
        resp = self.client.get(reverse("core:feed"), {"habilidad": python.pk})
        self.assertEqual(self._nombres(resp), [])

    # -- Nivel / experiencia (perfil del creador) ---------------------------

    def test_filtro_por_nivel(self):
        Perfil.objects.create(
            usuario=self.creador,
            nivel=Perfil.NIVEL_AVANZADO,
            experiencia_anios=6,
        )
        self._proyecto("Avanzado")
        self._proyecto("Normal", creador=self.otro)

        self._login()
        resp = self.client.get(
            reverse("core:feed"), {"nivel": Perfil.NIVEL_AVANZADO}
        )
        self.assertEqual(self._nombres(resp), ["Avanzado"])

    def test_filtro_por_experiencia_minima(self):
        Perfil.objects.create(
            usuario=self.creador,
            nivel=Perfil.NIVEL_INTERMEDIO,
            experiencia_anios=5,
        )
        Perfil.objects.create(
            usuario=self.otro,
            nivel=Perfil.NIVEL_PRINCIPIANTE,
            experiencia_anios=1,
        )
        self._proyecto("Senior")
        self._proyecto("Junior", creador=self.otro)

        self._login()
        resp = self.client.get(reverse("core:feed"), {"experiencia": "4"})
        self.assertEqual(self._nombres(resp), ["Senior"])

        resp = self.client.get(reverse("core:feed"), {"experiencia": "6"})
        self.assertEqual(self._nombres(resp), [])

    # -- Estados --------------------------------------------------------------

    def test_filtro_por_estado_vacante(self):
        proyecto_cubierto = self._proyecto("Cubierta")
        self._vacante(proyecto_cubierto, estado=Vacante.ESTADO_CUBIERTA)
        self._proyecto("Abierta")  # vacante por omisión abierta

        self._login()
        resp = self.client.get(
            reverse("core:feed"), {"estado_vacante": Vacante.ESTADO_CUBIERTA}
        )
        self.assertEqual(self._nombres(resp), ["Cubierta"])

    def test_filtro_por_estado_proyecto(self):
        self._proyecto("En Desarrollo", estado=Proyecto.ESTADO_EN_DESARROLLO)
        self._proyecto("Reclutando", estado=Proyecto.ESTADO_RECLUTANDO)

        self._login()
        resp = self.client.get(
            reverse("core:feed"), {"estado": Proyecto.ESTADO_EN_DESARROLLO}
        )
        self.assertEqual(self._nombres(resp), ["En Desarrollo"])

    def test_filtros_se_combinan_con_and(self):
        python = Tecnologia.objects.create(nombre="Python")
        proyecto = self._proyecto("Python Reclutando")
        vacante = self._vacante(proyecto)
        VacanteTecnologiaRequerida.objects.create(vacante=vacante, tecnologia=python)
        self._proyecto("Otro")

        self._login()
        resp = self.client.get(
            reverse("core:feed"),
            {"tecnologia": python.pk, "estado": Proyecto.ESTADO_RECLUTANDO},
        )
        self.assertEqual(self._nombres(resp), ["Python Reclutando"])

    def test_parametros_invalidos_no_rompen(self):
        self._proyecto("Sano")
        self._login()
        resp = self.client.get(
            reverse("core:feed"),
            {
                "habilidad": ["abc", "no-valida"],
                "tecnologia": "no-numerico",
                "nivel": "no-existe",
                "experiencia": "mucho",
                "estado": "no-existe",
                "estado_vacante": "no-existe",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._nombres(resp), ["Sano"])

        # Un id inexistente no rompe, simplemente no coincide con nada.
        resp = self.client.get(reverse("core:feed"), {"habilidad": "99999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._nombres(resp), [])