from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import ElementoLista, Lista, RegistroTitulo
from usuarios.models import Usuario


class RegistroTituloTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="valeria", email="valeria@example.com", password="Passw0rd-2026!"
        )
        self.media = Media.objects.create(
            titulo="Spider-Man", tipo=Media.Tipo.PELICULA, estado=Media.Estado.EN_CARTELERA
        )
        self.url = reverse("media-mi-registro", kwargs={"media_id": self.media.id})
        self.client.force_authenticate(self.usuario)

    def en_por_ver(self):
        return ElementoLista.objects.filter(
            lista__usuario=self.usuario, lista__tipo=Lista.Tipo.POR_VER, media=self.media
        ).exists()

    def test_requiere_autenticacion(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sin_registro_devuelve_valores_vacios(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"media_id": self.media.id, "estado": "", "me_gusta": False, "pendiente": False},
        )

    def test_media_inexistente_devuelve_404(self):
        url = reverse("media-mi-registro", kwargs={"media_id": 999999})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_marcar_viendo_y_me_gusta(self):
        response = self.client.patch(self.url, {"estado": "viendo", "me_gusta": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["estado"], "viendo")
        self.assertTrue(response.data["me_gusta"])
        registro = RegistroTitulo.objects.get(usuario=self.usuario, media=self.media)
        self.assertEqual(registro.estado, "viendo")

    def test_quitar_estado(self):
        self.client.patch(self.url, {"estado": "visto"}, format="json")
        response = self.client.patch(self.url, {"estado": ""}, format="json")
        self.assertEqual(response.data["estado"], "")

    def test_pendiente_usa_la_lista_por_ver(self):
        response = self.client.patch(self.url, {"pendiente": True}, format="json")
        self.assertTrue(response.data["pendiente"])
        self.assertTrue(self.en_por_ver())
        response = self.client.patch(self.url, {"pendiente": False}, format="json")
        self.assertFalse(response.data["pendiente"])
        self.assertFalse(self.en_por_ver())

    def test_marcar_visto_saca_de_por_ver(self):
        self.client.patch(self.url, {"pendiente": True}, format="json")
        response = self.client.patch(self.url, {"estado": "visto"}, format="json")
        self.assertFalse(response.data["pendiente"])
        self.assertFalse(self.en_por_ver())

    def test_estado_invalido_devuelve_400(self):
        response = self.client.patch(self.url, {"estado": "abandonado"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cuerpo_vacio_devuelve_400(self):
        response = self.client.patch(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resenar_marca_visto_y_saca_de_por_ver(self):
        self.client.patch(self.url, {"pendiente": True}, format="json")
        url = reverse("media-resenas", kwargs={"media_id": self.media.id})
        response = self.client.post(url, {"puntuacion": 8, "texto": "Buena"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        datos = self.client.get(self.url).data
        self.assertEqual(datos["estado"], "visto")
        self.assertFalse(datos["pendiente"])

    def test_resenar_mientras_se_ve_conserva_viendo(self):
        self.client.patch(self.url, {"estado": "viendo"}, format="json")
        url = reverse("media-resenas", kwargs={"media_id": self.media.id})
        self.client.post(url, {"puntuacion": 7}, format="json")
        self.assertEqual(self.client.get(self.url).data["estado"], "viendo")

    def test_proximo_estreno_no_se_puede_marcar_visto(self):
        self.media.estado = Media.Estado.PROXIMO_ESTRENO
        self.media.save()
        response = self.client.patch(self.url, {"estado": "visto"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(self.url, {"pendiente": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
