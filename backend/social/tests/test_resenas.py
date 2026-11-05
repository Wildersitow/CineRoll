from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import Resena
from usuarios.models import Usuario


class ResenasBase(APITestCase):
    def setUp(self):
        self.media = Media.objects.create(titulo="Película A", tipo=Media.Tipo.PELICULA)
        self.otra_media = Media.objects.create(titulo="Película B", tipo=Media.Tipo.PELICULA)
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
