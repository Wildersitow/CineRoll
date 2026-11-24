from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import ComentarioResena, Lista, ElementoLista, LikeResena, RegistroTitulo, Resena
from usuarios.models import Usuario


class BaseResenas(APITestCase):
    def setUp(self):
        self.autora = Usuario.objects.create_user(
            username="valeria", email="valeria@example.com", password="Passw0rd-2026!",
            avatar="https://img.example.com/valeria.png",
        )
        self.lector = Usuario.objects.create_user(
            username="sergio", email="sergio@example.com", password="Passw0rd-2026!"
        )
        self.media = Media.objects.create(
            titulo="Dune", tipo=Media.Tipo.PELICULA, estado=Media.Estado.EN_CARTELERA
        )
        self.resena = Resena.objects.create(
            usuario=self.autora, media=self.media, puntuacion=9, texto="Enorme"
        )


class LikeResenaTests(BaseResenas):
    def url(self, pk=None):
        return reverse("resena-like", kwargs={"pk": pk or self.resena.pk})

    def test_requiere_autenticacion(self):
        self.assertEqual(self.client.put(self.url()).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dar_y_quitar_like(self):
        self.client.force_authenticate(self.lector)
        response = self.client.put(self.url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"resena_id": self.resena.pk, "me_gusta": True, "total_likes": 1})
        # Repetir el PUT no duplica el like.
        self.assertEqual(self.client.put(self.url()).data["total_likes"], 1)
        response = self.client.delete(self.url())
        self.assertEqual(response.data, {"resena_id": self.resena.pk, "me_gusta": False, "total_likes": 0})

    def test_resena_oculta_devuelve_404(self):
        self.resena.oculta = True
        self.resena.save()
        self.client.force_authenticate(self.lector)
        self.assertEqual(self.client.put(self.url()).status_code, status.HTTP_404_NOT_FOUND)

    def test_listado_de_resenas_incluye_likes_comentarios_y_registro_del_autor(self):
        LikeResena.objects.create(usuario=self.lector, resena=self.resena)
        ComentarioResena.objects.create(usuario=self.lector, resena=self.resena, texto="¡Sí!")
        RegistroTitulo.objects.create(usuario=self.autora, media=self.media, estado="visto", me_gusta=True)
        self.client.force_authenticate(self.lector)
        url = reverse("media-resenas", kwargs={"media_id": self.media.pk})
        dato = self.client.get(url).data["results"][0]
        self.assertEqual(dato["total_likes"], 1)
        self.assertTrue(dato["me_gusta"])
        self.assertEqual(dato["total_comentarios"], 1)
        self.assertEqual(dato["estado_autor"], "visto")
        self.assertTrue(dato["autor_le_gusta"])
        self.assertEqual(dato["usuario_avatar"], "https://img.example.com/valeria.png")

    def test_anonimo_ve_me_gusta_falso(self):
        LikeResena.objects.create(usuario=self.lector, resena=self.resena)
        url = reverse("media-resenas", kwargs={"media_id": self.media.pk})
        dato = self.client.get(url).data["results"][0]
        self.assertFalse(dato["me_gusta"])
        self.assertEqual(dato["total_likes"], 1)
        self.assertEqual(dato["estado_autor"], "")


class ComentariosResenaTests(BaseResenas):
    def url(self):
        return reverse("resena-comentarios", kwargs={"pk": self.resena.pk})

    def test_comentar_y_listar(self):
        self.client.force_authenticate(self.lector)
        response = self.client.post(self.url(), {"texto": "  Totalmente de acuerdo  "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["texto"], "Totalmente de acuerdo")
        self.assertEqual(response.data["usuario"], "sergio")
        self.client.force_authenticate(None)
        listado = self.client.get(self.url()).data
        self.assertEqual(listado["count"], 1)

    def test_anonimo_no_puede_comentar(self):
        response = self.client.post(self.url(), {"texto": "Hola"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_comentario_vacio_devuelve_400(self):
        self.client.force_authenticate(self.lector)
        response = self.client.post(self.url(), {"texto": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_borrar_comentario_solo_autor_o_dueno_de_la_resena(self):
        tercero = Usuario.objects.create_user(
            username="tercero", email="t@example.com", password="Passw0rd-2026!"
        )
        comentario = ComentarioResena.objects.create(usuario=self.lector, resena=self.resena, texto="Hola")
        url = reverse("comentario-resena-detail", kwargs={"pk": comentario.pk})
        self.client.force_authenticate(tercero)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.autora)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ComentarioResena.objects.exists())


class EstadisticasMediaTests(BaseResenas):
    def test_estadisticas(self):
        RegistroTitulo.objects.create(usuario=self.autora, media=self.media, estado="visto", me_gusta=True)
        RegistroTitulo.objects.create(usuario=self.lector, media=self.media, estado="viendo")
        por_ver = Lista.objects.create(usuario=self.lector, nombre="Por ver", tipo=Lista.Tipo.POR_VER)
        ElementoLista.objects.create(lista=por_ver, media=self.media)
        publica = Lista.objects.create(usuario=self.lector, nombre="Ciencia ficción")
        ElementoLista.objects.create(lista=publica, media=self.media)
        url = reverse("media-estadisticas", kwargs={"media_id": self.media.pk})
        datos = self.client.get(url).data
        self.assertEqual(datos["promedio"], 9.0)
        self.assertEqual(datos["total_votos"], 1)
        self.assertEqual(datos["distribucion"]["9"], 1)
        self.assertEqual(datos["vistos"], 1)
        self.assertEqual(datos["viendo"], 1)
        self.assertEqual(datos["me_gusta"], 1)
        self.assertEqual(datos["pendientes"], 1)
        self.assertEqual(datos["resenas"], 1)
        self.assertEqual(datos["listas"], 1)

    def test_media_inexistente(self):
        url = reverse("media-estadisticas", kwargs={"media_id": 999999})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
