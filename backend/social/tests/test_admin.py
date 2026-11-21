from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from media.models import Media
from social.models import (
    ElementoLista,
    Lista,
    ReporteResena,
    Resena,
    Seguimiento,
    SugerenciaEdicion,
)
from usuarios.models import Usuario


class SocialAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_superuser(
            username="root", email="root@example.com", password="x"
        )
        cls.media = Media.objects.create(titulo="A", tipo=Media.Tipo.PELICULA)
        cls.lector = Usuario.objects.create_user(username="lector", password="x")
        cls.resena = Resena.objects.create(
            usuario=cls.lector, media=cls.media, puntuacion=1, texto="Spam"
        )
        cls.reporte = ReporteResena.objects.create(
            resena=cls.resena,
            usuario=cls.admin,
            motivo="Contenido ofensivo",
        )
        cls.lista = Lista.objects.create(
            usuario=cls.lector, nombre="Favoritas", tipo=Lista.Tipo.FAVORITAS
        )
        cls.elemento = ElementoLista.objects.create(
            lista=cls.lista, media=cls.media
        )
        cls.seguimiento = Seguimiento.objects.create(
            seguidor=cls.lector, seguido=cls.admin
        )
        cls.sugerencia = SugerenciaEdicion.objects.create(
            usuario=cls.lector,
            media=cls.media,
            campo="sinopsis",
            valor_propuesto="Sinopsis de prueba",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_modelos_estan_registrados(self):
        self.assertIn(Resena, admin.site._registry)
        self.assertIn(Lista, admin.site._registry)
        self.assertIn(ElementoLista, admin.site._registry)
        self.assertIn(Seguimiento, admin.site._registry)
        self.assertIn(SugerenciaEdicion, admin.site._registry)
        self.assertIn(ReporteResena, admin.site._registry)

    def test_paginas_del_admin(self):
        self.assertEqual(
            self.client.get(reverse("admin:social_resena_changelist")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("admin:social_resena_add")).status_code, 200
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:social_resena_change", args=[self.resena.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("admin:social_lista_changelist")).status_code, 200
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:social_lista_change", args=[self.lista.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:social_seguimiento_changelist")
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:social_sugerenciaedicion_changelist")
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:social_reporteresena_changelist")
            ).status_code,
            200,
        )

    def _accion(self, nombre):
        return self.client.post(
            reverse("admin:social_resena_changelist"),
            {"action": nombre, "_selected_action": [self.resena.pk]},
            follow=True,
        )

    def test_el_administrador_puede_ocultar_y_volver_a_mostrar(self):
        self._accion("ocultar_resenas")
        self.resena.refresh_from_db()
        self.assertTrue(self.resena.oculta)

        self._accion("mostrar_resenas")
        self.resena.refresh_from_db()
        self.assertFalse(self.resena.oculta)

    def test_el_administrador_puede_ocultar_resenas_desde_sus_reportes(self):
        response = self.client.post(
            reverse("admin:social_reporteresena_changelist"),
            {
                "action": "ocultar_resenas_reportadas",
                "_selected_action": [self.reporte.pk],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.resena.refresh_from_db()
        self.assertTrue(self.resena.oculta)

    def test_el_administrador_puede_borrar_resenas_inapropiadas(self):
        response = self.client.post(
            reverse("admin:social_resena_delete", args=[self.resena.pk]),
            {"post": "yes"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Resena.objects.exists())

    def test_accion_aprobar_sugerencia_aplica_cambio_y_registra_resolucion(self):
        url = reverse("admin:social_sugerenciaedicion_changelist")
        response = self.client.post(
            url,
            {
                "action": "aprobar_sugerencias",
                "_selected_action": [self.sugerencia.pk],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.sugerencia.refresh_from_db()
        self.media.refresh_from_db()
        self.assertEqual(self.sugerencia.estado, SugerenciaEdicion.Estado.APROBADA)
        self.assertEqual(self.sugerencia.revisado_por, self.admin)
        self.assertIsNotNone(self.sugerencia.fecha_resolucion)
        self.assertEqual(self.sugerencia.valor_anterior, "")
        self.assertEqual(self.media.sinopsis, "Sinopsis de prueba")

    def test_accion_rechazar_sugerencia_muestra_confirmacion_y_exige_motivo(self):
        url = reverse("admin:social_sugerenciaedicion_changelist")
        response = self.client.post(
            url,
            {
                "action": "rechazar_sugerencias",
                "_selected_action": [self.sugerencia.pk],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Motivo del rechazo")
        self.assertContains(response, "Sinopsis de prueba")
        self.sugerencia.refresh_from_db()
        self.assertEqual(self.sugerencia.estado, SugerenciaEdicion.Estado.PENDIENTE)

    def test_campos_resolucion_son_solo_lectura_en_admin(self):
        model_admin = admin.site._registry[SugerenciaEdicion]
        for campo in (
            "estado",
            "revisado_por",
            "fecha_resolucion",
            "motivo_rechazo",
            "valor_anterior",
            "valor_actual",
        ):
            self.assertIn(campo, model_admin.readonly_fields)


    def test_staff_con_permiso_de_lectura_no_puede_aprobar_sugerencias(self):
        self.lector.is_staff = True
        self.lector.save(update_fields=["is_staff"])
        self.lector.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="social", codename="view_sugerenciaedicion"
            )
        )
        self.client.force_login(self.lector)

        response = self.client.post(
            reverse("admin:social_sugerenciaedicion_changelist"),
            {"action": "aprobar_sugerencias", "_selected_action": [self.sugerencia.pk]},
        )
        self.assertEqual(response.status_code, 200)
        self.sugerencia.refresh_from_db()
        self.assertEqual(self.sugerencia.estado, SugerenciaEdicion.Estado.PENDIENTE)
        self.assertIsNone(response.context["action_form"])
