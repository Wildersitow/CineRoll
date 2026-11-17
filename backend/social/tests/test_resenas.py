from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import ReporteResena, Resena
from usuarios.models import Usuario


class ResenasBase(APITestCase):
    def setUp(self):
        self.media = Media.objects.create(
            titulo="Película A",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.EN_CARTELERA,
        )
        self.otra_media = Media.objects.create(
            titulo="Película B",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.FUERA_CARTELERA,
        )
        self.ana = Usuario.objects.create_user(username="ana", email="ana@example.com", password="x")
        self.beto = Usuario.objects.create_user(username="beto", email="beto@example.com", password="x")
        self.url_lista = reverse("media-resenas", kwargs={"media_id": self.media.pk})

    def detalle(self, resena):
        return reverse("resena-detail", kwargs={"pk": resena.pk})


class CrearResenaTests(ResenasBase):
    def test_visitante_no_puede_reseñar(self):
        response = self.client.post(self.url_lista, {"puntuacion": 8})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Resena.objects.count(), 0)

    def test_usuario_crea_su_reseña(self):
        self.client.force_authenticate(self.ana)

        response = self.client.post(self.url_lista, {"puntuacion": 8, "texto": "Muy buena."})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        resena = Resena.objects.get()
        self.assertEqual((resena.usuario, resena.media, resena.puntuacion), (self.ana, self.media, 8))
        self.assertEqual(response.data["usuario"], "ana")
        self.assertEqual(response.data["media_id"], self.media.pk)

    def test_texto_es_opcional(self):
        self.client.force_authenticate(self.ana)

        response = self.client.post(self.url_lista, {"puntuacion": 5})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["texto"], "")

    def test_texto_normaliza_espacios_y_espacios_solos_quedan_vacios(self):
        self.client.force_authenticate(self.ana)
        response = self.client.post(
            self.url_lista,
            {"puntuacion": 5, "texto": "  Muy   buena \n película.  "},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["texto"], "Muy buena película.")

        self.client.force_authenticate(self.beto)
        empty_response = self.client.post(
            self.url_lista,
            {"puntuacion": 6, "texto": " \n\t  "},
        )

        self.assertEqual(empty_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(empty_response.data["texto"], "")

    def test_texto_admite_hasta_5000_caracteres_y_rechaza_mas(self):
        self.client.force_authenticate(self.ana)
        accepted = self.client.post(
            self.url_lista,
            {"puntuacion": 5, "texto": "x" * 5000},
        )

        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(accepted.data["texto"]), 5000)

        self.client.force_authenticate(self.beto)
        rejected = self.client.post(
            self.url_lista,
            {"puntuacion": 5, "texto": "x" * 5001},
        )

        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("texto", rejected.data["error"]["campos"])
        self.assertEqual(Resena.objects.count(), 1)

    def test_no_se_puede_reseñar_un_proximo_estreno(self):
        self.client.force_authenticate(self.ana)
        self.media.estado = Media.Estado.PROXIMO_ESTRENO
        self.media.save(update_fields=["estado"])
        response = self.client.post(self.url_lista, {"puntuacion": 8})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "próximos a estrenarse",
            response.data["error"]["mensaje"],
        )
        self.assertFalse(Resena.objects.exists())

    def test_no_se_puede_editar_resena_si_titulo_pasa_a_proximo_estreno(self):
        review = Resena.objects.create(
            usuario=self.ana,
            media=self.media,
            puntuacion=8,
            texto="Original",
        )
        self.media.estado = Media.Estado.PROXIMO_ESTRENO
        self.media.save(update_fields=["estado"])
        self.client.force_authenticate(self.ana)

        response = self.client.patch(
            self.detalle(review),
            {"texto": "Editada"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "próximos a estrenarse",
            response.data["error"]["mensaje"],
        )
        review.refresh_from_db()
        self.assertEqual(review.texto, "Original")

    def test_se_puede_reseñar_en_cartelera_y_fuera_de_cartelera(self):
        self.client.force_authenticate(self.ana)
        for title, state in (
            (self.media, Media.Estado.EN_CARTELERA),
            (self.otra_media, Media.Estado.FUERA_CARTELERA),
        ):
            with self.subTest(state=state):
                title.estado = state
                title.save(update_fields=["estado"])
                response = self.client.post(
                    reverse("media-resenas", kwargs={"media_id": title.pk}),
                    {"puntuacion": 8},
                )

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_no_se_puede_suplantar_a_otro_usuario_ni_cambiar_de_titulo(self):
        self.client.force_authenticate(self.ana)

        self.client.post(
            self.url_lista,
            {"puntuacion": 7, "usuario": self.beto.pk, "usuario_id": self.beto.pk, "media_id": self.otra_media.pk},
        )

        resena = Resena.objects.get()
        self.assertEqual(resena.usuario, self.ana)
        self.assertEqual(resena.media, self.media)

    def test_puntuacion_fuera_de_rango_o_invalida(self):
        self.client.force_authenticate(self.ana)

        for valor in (0, 11, -1, "abc", 7.5, None):
            with self.subTest(puntuacion=valor):
                response = self.client.post(self.url_lista, {"puntuacion": valor}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(self.url_lista, {}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Resena.objects.count(), 0)

    def test_limites_validos(self):
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.client.post(self.url_lista, {"puntuacion": 1}).status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.beto)
        self.assertEqual(self.client.post(self.url_lista, {"puntuacion": 10}).status_code, status.HTTP_201_CREATED)

    def test_una_sola_reseña_por_usuario_y_titulo(self):
        self.client.force_authenticate(self.ana)
        self.client.post(self.url_lista, {"puntuacion": 8})

        repetida = self.client.post(self.url_lista, {"puntuacion": 3})

        self.assertEqual(repetida.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Resena.objects.count(), 1)
        self.assertEqual(Resena.objects.get().puntuacion, 8)

    def test_el_mismo_usuario_puede_reseñar_otro_titulo(self):
        self.client.force_authenticate(self.ana)
        self.client.post(self.url_lista, {"puntuacion": 8})

        response = self.client.post(
            reverse("media-resenas", kwargs={"media_id": self.otra_media.pk}), {"puntuacion": 6}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_titulo_inexistente(self):
        self.client.force_authenticate(self.ana)
        url = reverse("media-resenas", kwargs={"media_id": 999999})

        self.assertEqual(self.client.post(url, {"puntuacion": 8}).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_la_base_de_datos_tambien_protege_los_limites_y_duplicados(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resena.objects.create(usuario=self.ana, media=self.media, puntuacion=11)

        Resena.objects.create(usuario=self.ana, media=self.media, puntuacion=5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resena.objects.create(usuario=self.ana, media=self.media, puntuacion=6)


class ListarResenasTests(ResenasBase):
    def test_listado_publico_paginado_y_mas_recientes_primero(self):
        primera = Resena.objects.create(usuario=self.ana, media=self.media, puntuacion=8, texto="Primera")
        segunda = Resena.objects.create(usuario=self.beto, media=self.media, puntuacion=6, texto="Segunda")
        Resena.objects.create(usuario=self.ana, media=self.otra_media, puntuacion=2)  # otro título

        response = self.client.get(self.url_lista)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual([r["id"] for r in response.data["results"]], [segunda.pk, primera.pk])

    def test_feed_publico_filtra_con_texto_y_por_media(self):
        text_review = Resena.objects.create(
            usuario=self.ana,
            media=self.media,
            puntuacion=8,
            texto="Recomendado",
        )
        no_text_review = Resena.objects.create(
            usuario=self.beto,
            media=self.media,
            puntuacion=6,
        )
        other_title_review = Resena.objects.create(
            usuario=Usuario.objects.create_user(username="carla", password="x"),
            media=self.otra_media,
            puntuacion=9,
            texto="Otro título",
        )
        Resena.objects.create(
            usuario=Usuario.objects.create_user(username="diego", password="x"),
            media=self.media,
            puntuacion=1,
            texto="Moderación",
            oculta=True,
        )

        feed_url = reverse("resenas-list")
        all_reviews = self.client.get(feed_url)
        with_text = self.client.get(feed_url, {"con_texto": "true"})
        without_text = self.client.get(feed_url, {"con_texto": "false"})
        by_title = self.client.get(feed_url, {"media": self.otra_media.pk})

        self.assertEqual(all_reviews.data["count"], 3)
        self.assertEqual(
            [item["id"] for item in all_reviews.data["results"]],
            [other_title_review.pk, no_text_review.pk, text_review.pk],
        )
        self.assertEqual(
            {item["id"] for item in with_text.data["results"]},
            {text_review.pk, other_title_review.pk},
        )
        self.assertEqual(
            [item["id"] for item in without_text.data["results"]],
            [no_text_review.pk],
        )
        self.assertEqual(
            [item["id"] for item in by_title.data["results"]],
            [other_title_review.pk],
        )

    def test_feed_rechaza_filtros_invalidos(self):
        feed_url = reverse("resenas-list")

        invalid_boolean = self.client.get(feed_url, {"con_texto": "yes"})
        invalid_media = self.client.get(feed_url, {"media": "abc"})

        self.assertEqual(invalid_boolean.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_media.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feed_uses_constant_queries(self):
        for index in range(5):
            usuario = Usuario.objects.create_user(
                username=f"feed-{index}",
                password="x",
            )
            Resena.objects.create(
                usuario=usuario,
                media=self.media,
                puntuacion=5,
                texto=f"Reseña {index}",
            )

        with self.assertNumQueries(2):
            response = self.client.get(reverse("resenas-list"))

        self.assertEqual(response.data["count"], 5)

    def test_paginacion(self):
        for i in range(25):
            usuario = Usuario.objects.create_user(username=f"u{i}", password="x")
            Resena.objects.create(usuario=usuario, media=self.media, puntuacion=5)

        pagina1 = self.client.get(self.url_lista)
        pagina2 = self.client.get(self.url_lista, {"page": 2})

        self.assertEqual(pagina1.data["count"], 25)
        self.assertEqual(len(pagina1.data["results"]), 20)
        self.assertEqual(len(pagina2.data["results"]), 5)

    def test_las_ocultas_no_aparecen(self):
        Resena.objects.create(usuario=self.ana, media=self.media, puntuacion=8)
        oculta = Resena.objects.create(usuario=self.beto, media=self.media, puntuacion=1, oculta=True)

        response = self.client.get(self.url_lista)

        self.assertEqual(response.data["count"], 1)
        self.assertNotIn(oculta.pk, [r["id"] for r in response.data["results"]])
        self.assertEqual(self.client.get(self.detalle(oculta)).status_code, status.HTTP_404_NOT_FOUND)

    def test_el_listado_no_hace_una_consulta_por_reseña(self):
        for i in range(5):
            usuario = Usuario.objects.create_user(username=f"u{i}", password="x")
            Resena.objects.create(usuario=usuario, media=self.media, puntuacion=5)

        with self.assertNumQueries(3):  # media + conteo + reseñas con su usuario
            self.client.get(self.url_lista)


class EditarYBorrarResenaTests(ResenasBase):
    def setUp(self):
        super().setUp()
        self.resena = Resena.objects.create(usuario=self.ana, media=self.media, puntuacion=8, texto="Original")

    def test_cualquiera_puede_ver_una_reseña(self):
        response = self.client.get(self.detalle(self.resena))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["texto"], "Original")

    def test_el_autor_edita_su_reseña(self):
        self.client.force_authenticate(self.ana)

        response = self.client.patch(self.detalle(self.resena), {"puntuacion": 9, "texto": "Editada"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resena.refresh_from_db()
        self.assertEqual((self.resena.puntuacion, self.resena.texto), (9, "Editada"))

    def test_editar_no_permite_mover_la_reseña_a_otro_titulo_ni_usuario(self):
        self.client.force_authenticate(self.ana)

        self.client.patch(self.detalle(self.resena), {"media_id": self.otra_media.pk, "usuario_id": self.beto.pk})

        self.resena.refresh_from_db()
        self.assertEqual((self.resena.media, self.resena.usuario), (self.media, self.ana))

    def test_el_autor_borra_su_reseña(self):
        self.client.force_authenticate(self.ana)

        response = self.client.delete(self.detalle(self.resena))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Resena.objects.exists())

    def test_otro_usuario_no_puede_editar_ni_borrar_reseñas_ajenas(self):
        self.client.force_authenticate(self.beto)

        for metodo, datos in (("patch", {"puntuacion": 1}), ("put", {"puntuacion": 1}), ("delete", None)):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.detalle(self.resena), datos)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.resena.refresh_from_db()
        self.assertEqual((self.resena.puntuacion, self.resena.texto), (8, "Original"))

    def test_visitante_no_puede_modificar(self):
        for metodo, datos in (("patch", {"puntuacion": 1}), ("delete", None)):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.detalle(self.resena), datos)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Resena.objects.filter(pk=self.resena.pk).exists())

    def test_editar_valida_la_puntuacion(self):
        self.client.force_authenticate(self.ana)

        response = self.client.patch(self.detalle(self.resena), {"puntuacion": 99})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReportarResenaTests(ResenasBase):
    def setUp(self):
        super().setUp()
        self.resena = Resena.objects.create(
            usuario=self.ana,
            media=self.media,
            puntuacion=8,
            texto="Reseña para reportar",
        )
        self.url = reverse("resena-reportar", kwargs={"pk": self.resena.pk})

    def test_usuario_autenticado_puede_reportar_una_resena(self):
        self.client.force_authenticate(self.beto)

        response = self.client.post(self.url, {"motivo": "Contenido ofensivo"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reporte = ReporteResena.objects.get()
        self.assertEqual((reporte.resena, reporte.usuario), (self.resena, self.beto))
        self.assertEqual(reporte.motivo, "Contenido ofensivo")
        self.assertEqual(response.data["resena"], self.resena.pk)
        self.assertEqual(response.data["usuario"], self.beto.pk)
        self.assertIn("fecha", response.data)

    def test_visitante_no_puede_reportar(self):
        response = self.client.post(self.url, {"motivo": "Contenido ofensivo"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(ReporteResena.objects.exists())

    def test_un_usuario_no_puede_reportar_dos_veces_la_misma_resena(self):
        self.client.force_authenticate(self.beto)
        self.client.post(self.url, {"motivo": "Contenido ofensivo"})

        response = self.client.post(self.url, {"motivo": "Otro motivo"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ya reportaste esta reseña", str(response.data))
        self.assertEqual(ReporteResena.objects.count(), 1)

    def test_usuarios_distintos_pueden_reportar_la_misma_resena(self):
        carla = Usuario.objects.create_user(username="carla", password="x")
        for usuario in (self.beto, carla):
            self.client.force_authenticate(usuario)
            response = self.client.post(self.url, {"motivo": "Contenido ofensivo"})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(ReporteResena.objects.filter(resena=self.resena).count(), 2)

    def test_motivo_es_obligatorio_y_no_puede_ser_vacio(self):
        self.client.force_authenticate(self.beto)

        for datos in ({}, {"motivo": "   "}):
            with self.subTest(datos=datos):
                response = self.client.post(self.url, datos)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(ReporteResena.objects.exists())

    def test_no_se_puede_reportar_una_resena_oculta_o_inexistente(self):
        self.client.force_authenticate(self.beto)
        self.resena.oculta = True
        self.resena.save(update_fields=["oculta"])

        response = self.client.post(self.url, {"motivo": "Contenido ofensivo"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(ReporteResena.objects.exists())
