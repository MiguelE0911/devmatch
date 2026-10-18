from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import Proyecto, ProyectoMedia, Vacante
from apps.projects.tests.helpers import lleva_a

import json

Usuario = get_user_model()


class GaleriaViewsTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-galeria@devmatch.test", "creador-galeria", password="Clave-123!"
        )
        self.otro = Usuario.objects.create_user(
            "otro-galeria@devmatch.test", "otro-galeria", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador,
            nombre="Demo",
            descripcion="desc",
            estado=Proyecto.ESTADO_RECLUTANDO,
        )
        self.base = reverse("projects:project_detail", args=[self.proyecto.pk])

    def test_galeria_usuario_anonimo_redirige_al_login(self):
        resp = self.client.get(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith("/ingresar/"))

    def test_galeria_solo_el_dueno_accede(self):
        self.client.force_login(self.otro)
        resp = self.client.get(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk])
        )
        self.assertRedirects(resp, self.base)

    def test_galeria_usa_la_plantilla_correcta(self):
        self.client.force_login(self.creador)
        resp = self.client.get(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "projects/gallery_form.html")
        self.assertContains(resp, "Editar galería")

    def test_galeria_muestra_imagenes_activas(self):
        ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/proto.png",
            orden=0,
        )
        self.client.force_login(self.creador)
        resp = self.client.get(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "https://example.com/proto.png")

    def test_post_crea_imagen_prototipo_activa(self):
        self.client.force_login(self.creador)
        resp = self.client.post(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk]),
            {"archivo_url": "https://example.com/proto.png", "orden": "0"},
        )
        self.assertRedirects(resp, self.base + "?tab=galeria")
        media = ProyectoMedia.objects.get()
        self.assertEqual(media.proyecto, self.proyecto)
        self.assertEqual(media.tipo, ProyectoMedia.TIPO_PROTOTIPO)
        self.assertTrue(media.es_activo)

    def test_post_sin_orden_apila_al_final(self):
        ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/proto-1.png",
            orden=4,
        )
        self.client.force_login(self.creador)
        resp = self.client.post(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk]),
            {"archivo_url": "https://example.com/proto-2.png", "orden": ""},
        )
        self.assertRedirects(resp, self.base + "?tab=galeria")
        nueva = ProyectoMedia.objects.get(archivo_url="https://example.com/proto-2.png")
        self.assertEqual(nueva.orden, 5)

    def test_post_con_url_invalida_no_crea_imagen(self):
        self.client.force_login(self.creador)
        resp = self.client.post(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk]),
            {"archivo_url": "no-sirve", "orden": "0"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ProyectoMedia.objects.exists())

    def test_solo_el_dueno_crea_imagenes(self):
        self.client.force_login(self.otro)
        resp = self.client.post(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk]),
            {"archivo_url": "https://example.com/proto.png", "orden": "0"},
        )
        self.assertRedirects(resp, self.base)
        self.assertFalse(ProyectoMedia.objects.exists())

    def test_post_desactiva_imagen(self):
        media = ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/proto.png",
            orden=0,
        )
        self.client.force_login(self.creador)
        resp = self.client.post(reverse("projects:media_delete", args=[media.pk]))
        self.assertRedirects(resp, self.base + "?tab=galeria")
        media.refresh_from_db()
        self.assertFalse(media.es_activo)

    def test_solo_el_dueno_desactiva_imagenes(self):
        media = ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/proto.png",
            orden=0,
        )
        self.client.force_login(self.otro)
        resp = self.client.post(reverse("projects:media_delete", args=[media.pk]))
        self.assertRedirects(resp, self.base)
        media.refresh_from_db()
        self.assertTrue(media.es_activo)

    def test_no_se_vuelve_a_desactivar_una_imagen_ya_oculta(self):
        media = ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/proto.png",
            orden=0,
            es_activo=False,
        )
        self.client.force_login(self.creador)
        resp = self.client.post(reverse("projects:media_delete", args=[media.pk]))
        self.assertEqual(resp.status_code, 404)


class GaleriaReorderTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-reorden@devmatch.test", "creador-reorden", password="Clave-123!"
        )
        self.otro = Usuario.objects.create_user(
            "otro-reorden@devmatch.test", "otro-reorden", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.media = [
            ProyectoMedia.objects.create(
                proyecto=self.proyecto,
                tipo=ProyectoMedia.TIPO_PROTOTIPO,
                archivo_url=f"https://example.com/proto-{i}.png",
                orden=i,
            )
            for i in range(3)
        ]
        self.url = reverse("projects:media_reorder", args=[self.proyecto.pk])

    def post_ids(self, ids):
        return self.client.post(
            self.url, data=json.dumps({"ids": ids}), content_type="application/json"
        )

    def ordenes(self):
        return [
            m.orden
            for m in ProyectoMedia.objects.filter(
                proyecto=self.proyecto,
                tipo=ProyectoMedia.TIPO_PROTOTIPO,
                es_activo=True,
            ).order_by("pk")
        ]

    def test_reordena_y_persiste_el_nuevo_orden(self):
        self.client.force_login(self.creador)
        nuevo_orden = [self.media[2].pk, self.media[0].pk, self.media[1].pk]
        resp = self.post_ids(nuevo_orden)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertEqual(self.ordenes(), [1, 2, 0])

    def test_solo_el_dueno_reordena(self):
        self.client.force_login(self.otro)
        resp = self.post_ids([self.media[2].pk, self.media[0].pk, self.media[1].pk])
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.ordenes(), [0, 1, 2])

    def test_ids_que_no_coinciden_con_las_activas_rechaza(self):
        self.client.force_login(self.creador)
        resp = self.post_ids([self.media[0].pk, self.media[1].pk])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.ordenes(), [0, 1, 2])

    def test_ids_duplicados_rechaza(self):
        self.client.force_login(self.creador)
        resp = self.post_ids(
            [self.media[0].pk, self.media[1].pk, self.media[1].pk]
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.ordenes(), [0, 1, 2])

    def test_json_invalido_rechaza(self):
        self.client.force_login(self.creador)
        resp = self.client.post(self.url, data="no-json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_ignora_las_imagenes_desactivadas_en_el_orden(self):
        ProyectoMedia.objects.create(
            proyecto=self.proyecto,
            tipo=ProyectoMedia.TIPO_PROTOTIPO,
            archivo_url="https://example.com/proto-oculto.png",
            orden=9,
            es_activo=False,
        )
        self.client.force_login(self.creador)
        nuevo_orden = [self.media[2].pk, self.media[0].pk, self.media[1].pk]
        resp = self.post_ids(nuevo_orden)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.ordenes(), [1, 2, 0])
        oculta = ProyectoMedia.objects.get(archivo_url="https://example.com/proto-oculto.png")
        self.assertEqual(oculta.orden, 9)


class ProyectoDeleteTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-delete@devmatch.test", "creador-delete", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.url = reverse("projects:project_delete", args=[self.proyecto.pk])

    def test_borrar_proyecto_en_reclutando_lo_cancela(self):
        lleva_a(self.proyecto, Proyecto.ESTADO_RECLUTANDO)
        self.client.force_login(self.creador)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, Proyecto.ESTADO_CANCELADO)
        self.assertIsNotNone(self.proyecto.cancelado_en)
        self.assertFalse(self.proyecto.es_activo)
        self.assertIsNotNone(self.proyecto.desactivado_en)
        self.assertEqual(self.proyecto.desactivado_por, self.creador)

    def test_borrar_proyecto_finalizado_no_cambia_estado_pero_desactiva(self):
        lleva_a(self.proyecto, Proyecto.ESTADO_FINALIZADO)
        self.client.force_login(self.creador)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, Proyecto.ESTADO_FINALIZADO)
        self.assertFalse(self.proyecto.es_activo)
        self.assertIsNotNone(self.proyecto.desactivado_en)
        self.assertEqual(self.proyecto.desactivado_por, self.creador)


class ProyectoDetailVisibilidadTests(TestCase):
    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-visibilidad@devmatch.test",
            "creador-visibilidad",
            password="Clave-123!",
        )
        self.otro = Usuario.objects.create_user(
            "otro-visibilidad@devmatch.test", "otro-visibilidad", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.url = reverse("projects:project_detail", args=[self.proyecto.pk])

    def test_anonimo_no_ve_borrador(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_otro_dueno_no_ve_borrador(self):
        self.client.force_login(self.otro)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_dueno_si_ve_su_borrador(self):
        self.client.force_login(self.creador)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_anonimo_no_ve_cancelado(self):
        self.proyecto.estado = Proyecto.ESTADO_CANCELADO
        self.proyecto.cancelado_en = timezone.now()
        self.proyecto.save()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_tercero_ve_estados_visibles(self):
        lleva_a(self.proyecto, Proyecto.ESTADO_RECLUTANDO)
        self.client.force_login(self.otro)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_anonimo_redirige_a_login_en_vista_protegida(self):
        resp = self.client.get(
            reverse("projects:project_delete", args=[self.proyecto.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith("/ingresar/"))


class ProyectoVolverTests(TestCase):
    """El botón "Volver" del detalle es determinista: nunca history.back()."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-volver@devmatch.test", "creador-volver", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador,
            nombre="Demo",
            descripcion="desc",
            estado=Proyecto.ESTADO_RECLUTANDO,
        )
        self.url = reverse("projects:project_detail", args=[self.proyecto.pk])

    def test_volver_apunta_al_feed_y_no_usa_history_back(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, reverse("core:feed"))
        self.assertNotContains(resp, "history.back()")

    def test_volver_honra_un_next_interno(self):
        resp = self.client.get(self.url, {"next": "/home/?tecnologia=1"})
        self.assertContains(resp, "/home/?tecnologia=1")

    def test_volver_ignora_un_next_externo(self):
        resp = self.client.get(self.url, {"next": "https://evil.example.com/"})
        self.assertNotContains(resp, 'href="https://evil.example.com')
        self.assertContains(resp, reverse("core:feed"))

    def test_volver_vuelve_a_la_pagina_del_feed(self):
        resp = self.client.get(self.url, {"next": "/home/?pagina=2"})
        self.assertContains(resp, 'href="/home/?pagina=2"')


class ProyectoPostulacionBloqueadaTests(TestCase):
    """Un proyecto finalizado ya no muestra vacantes postulables."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-bloqueo@devmatch.test", "creador-bloqueo", password="Clave-123!"
        )
        self.otro = Usuario.objects.create_user(
            "otro-bloqueo@devmatch.test", "otro-bloqueo", password="Clave-123!"
        )
        self.proyecto = Proyecto.objects.create(
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.vacante = Vacante.objects.create(
            proyecto=self.proyecto,
            titulo="Backend",
            descripcion="desc",
            cupos_totales=2,
        )
        self.url = reverse("projects:project_detail", args=[self.proyecto.pk])

    def test_vacante_no_postulable_en_proyecto_finalizado(self):
        lleva_a(self.proyecto, Proyecto.ESTADO_FINALIZADO)
        self.client.force_login(self.otro)
        resp = self.client.get(self.url, {"tab": "vacantes"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "El proyecto ya no está abierto a postulaciones")


class ProyectoCreateModalTests(TestCase):
    """El modal de crear proyecto se sirve como fragmento por AJAX y devuelve
    JSON al crear; sin AJAX conserva el flujo de página completa."""

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-modal@devmatch.test", "creador-modal", password="Clave-123!"
        )
        self.client.force_login(self.creador)
        self.url = reverse("projects:project_create")
        self.datos = {"nombre": "Nuevo", "descripcion": "desc", "logo_url": ""}

    def test_get_ajax_devuelve_el_fragmento_del_modal(self):
        resp = self.client.get(self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "projects/_project_create_modal.html")
        self.assertTemplateNotUsed(resp, "projects/project_create.html")
        self.assertContains(resp, "data-crear-form")

    def test_get_normal_devuelve_la_pagina_completa(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "projects/project_create.html")

    def test_post_ajax_valido_devuelve_json_con_redirect(self):
        resp = self.client.post(
            self.url, self.datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        proyecto = Proyecto.objects.get(nombre="Nuevo")
        self.assertEqual(data["redirect"], reverse("projects:project_detail", args=[proyecto.pk]))

    def test_post_ajax_invalido_devuelve_422_con_errores(self):
        resp = self.client.post(
            self.url,
            {"nombre": "", "descripcion": "desc", "logo_url": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 422)
        self.assertTemplateUsed(resp, "projects/_project_create_modal.html")
        self.assertFalse(Proyecto.objects.filter(nombre="Nuevo").exists())

    def test_post_normal_redirige_al_detalle(self):
        resp = self.client.post(self.url, self.datos)
        self.assertEqual(resp.status_code, 302)
        proyecto = Proyecto.objects.get(nombre="Nuevo")
        self.assertEqual(
            resp.url, reverse("projects:project_detail", args=[proyecto.pk])
        )


class VacancyCreateEstadoTests(TestCase):
    """Solo se agregan vacantes a proyectos abiertos (ni finalizado ni
    cancelado). El bloqueo recae en el alta; editar/borrar no se toca."""

    ESTADOS_PERMITIDOS = (
        Proyecto.ESTADO_BORRADOR,
        Proyecto.ESTADO_PUBLICADO,
        Proyecto.ESTADO_RECLUTANDO,
        Proyecto.ESTADO_EQUIPO_COMPLETO,
        Proyecto.ESTADO_EN_DESARROLLO,
    )
    ESTADOS_BLOQUEADOS = (
        Proyecto.ESTADO_FINALIZADO,
        Proyecto.ESTADO_CANCELADO,
    )
    DATOS = {"titulo": "Backend", "descripcion": "desc", "cupos_totales": "2"}

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-vac-estado@devmatch.test",
            "creador-vac-estado",
            password="Clave-123!",
        )
        self.client.force_login(self.creador)

    def _proyecto_en(self, estado):
        proyecto = Proyecto.objects.create(
            creador=self.creador, nombre=f"Demo {estado}", descripcion="desc"
        )
        if estado != Proyecto.ESTADO_BORRADOR:
            lleva_a(proyecto, estado)
        return proyecto

    def test_permite_agregar_en_estados_abiertos(self):
        for estado in self.ESTADOS_PERMITIDOS:
            with self.subTest(estado=estado):
                proyecto = self._proyecto_en(estado)
                url = reverse("projects:vacancy_create", args=[proyecto.pk])
                resp = self.client.post(url, self.DATOS)
                self.assertEqual(resp.status_code, 302)
                self.assertTrue(proyecto.vacantes.filter(titulo="Backend").exists())

    def test_bloquea_agregar_en_estados_cerrados(self):
        for estado in self.ESTADOS_BLOQUEADOS:
            with self.subTest(estado=estado):
                proyecto = self._proyecto_en(estado)
                url = reverse("projects:vacancy_create", args=[proyecto.pk])

                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 302)
                self.assertIn("?tab=vacantes", resp.url)

                resp = self.client.post(url, self.DATOS)
                self.assertEqual(resp.status_code, 302)
                self.assertIn("?tab=vacantes", resp.url)
                self.assertFalse(proyecto.vacantes.filter(titulo="Backend").exists())

    def test_detalle_del_dueno_muestra_cta_en_proyecto_abierto(self):
        proyecto = self._proyecto_en(Proyecto.ESTADO_RECLUTANDO)
        resp = self.client.get(
            reverse("projects:project_detail", args=[proyecto.pk]),
            {"tab": "vacantes"},
        )
        self.assertContains(resp, "Añadir vacante")
        self.assertNotContains(resp, "No se pueden añadir vacantes")

    def test_detalle_del_dueno_oculta_cta_en_proyecto_cerrado(self):
        proyecto = self._proyecto_en(Proyecto.ESTADO_FINALIZADO)
        resp = self.client.get(
            reverse("projects:project_detail", args=[proyecto.pk]),
            {"tab": "vacantes"},
        )
        self.assertNotContains(resp, "Añadir vacante")
        self.assertContains(resp, "No se pueden añadir vacantes")


class GaleriaAgregarImagenEstadoTests(TestCase):
    """Solo se agregan imágenes a proyectos NO cancelados.

    Un proyecto `finalizado` SÍ puede seguir subiendo imágenes de prototipos.
    """

    ESTADOS_PERMITIDOS = (
        Proyecto.ESTADO_BORRADOR,
        Proyecto.ESTADO_PUBLICADO,
        Proyecto.ESTADO_RECLUTANDO,
        Proyecto.ESTADO_EQUIPO_COMPLETO,
        Proyecto.ESTADO_EN_DESARROLLO,
        Proyecto.ESTADO_FINALIZADO,
    )

    def setUp(self):
        self.creador = Usuario.objects.create_user(
            "creador-gal-estado@devmatch.test",
            "creador-gal-estado",
            password="Clave-123!",
        )
        self.client.force_login(self.creador)

    def _proyecto_en(self, estado):
        proyecto = Proyecto.objects.create(
            creador=self.creador, nombre=f"Demo {estado}", descripcion="desc"
        )
        if estado != Proyecto.ESTADO_BORRADOR:
            lleva_a(proyecto, estado)
        return proyecto

    def test_permite_agregar_imagen_salvo_cancelado(self):
        for estado in self.ESTADOS_PERMITIDOS:
            with self.subTest(estado=estado):
                proyecto = self._proyecto_en(estado)
                url = reverse("projects:project_gallery_edit", args=[proyecto.pk])
                resp = self.client.post(url, {"archivo_url": "https://e.com/img.png"})
                self.assertEqual(resp.status_code, 302)
                self.assertTrue(
                    proyecto.media.filter(
                        tipo=ProyectoMedia.TIPO_PROTOTIPO,
                        archivo_url="https://e.com/img.png",
                        es_activo=True,
                    ).exists()
                )

    def test_bloquea_agregar_imagen_en_cancelado(self):
        proyecto = self._proyecto_en(Proyecto.ESTADO_CANCELADO)
        url = reverse("projects:project_gallery_edit", args=[proyecto.pk])

        # El dueño sí puede entrar (para borrar/reordenar), pero el formulario
        # de alta no se muestra y aparece el aviso.
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Subir imagen")
        self.assertContains(resp, "No se pueden añadir imágenes")

        resp = self.client.post(url, {"archivo_url": "https://e.com/img.png"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("?tab=galeria", resp.url)
        self.assertFalse(
            proyecto.media.filter(
                tipo=ProyectoMedia.TIPO_PROTOTIPO,
                archivo_url="https://e.com/img.png",
            ).exists()
        )

    def test_formulario_de_alta_visible_en_estado_permitido(self):
        proyecto = self._proyecto_en(Proyecto.ESTADO_FINALIZADO)
        url = reverse("projects:project_gallery_edit", args=[proyecto.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Subir imagen")
        self.assertNotContains(resp, "No se pueden añadir imágenes")