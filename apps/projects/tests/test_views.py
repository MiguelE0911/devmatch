from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.projects.models import Proyecto, ProyectoMedia

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
            creador=self.creador, nombre="Demo", descripcion="desc"
        )
        self.base = reverse("projects:project_detail", args=[self.proyecto.pk])

    def test_galeria_usuario_anonimo_redirige_al_login(self):
        resp = self.client.get(
            reverse("projects:project_gallery_edit", args=[self.proyecto.pk])
        )
        self.assertEqual(resp.status_code, 302)

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
        self.proyecto.estado = Proyecto.ESTADO_RECLUTANDO
        self.proyecto.save()
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
        self.proyecto.estado = Proyecto.ESTADO_FINALIZADO
        self.proyecto.save()
        self.client.force_login(self.creador)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, Proyecto.ESTADO_FINALIZADO)
        self.assertFalse(self.proyecto.es_activo)
        self.assertIsNotNone(self.proyecto.desactivado_en)
        self.assertEqual(self.proyecto.desactivado_por, self.creador)