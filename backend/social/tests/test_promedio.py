from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Genero, Media
from social.models import Resena
from social.services import anotar_puntuacion, resumen_puntuacion
from usuarios.models import Usuario


def crear_usuarios(cantidad):
    return [Usuario.objects.create_user(username=f"u{i}", password="x") for i in range(cantidad)]


class ResumenPuntuacionTests(TestCase):
    def setUp(self):
        self.media = Media.objects.create(titulo="A", tipo=Media.Tipo.PELICULA)
        self.usuarios = crear_usuarios(4)

    def test_sin_votos(self):
        self.assertEqual(resumen_puntuacion(self.media.pk), {"promedio": None, "total_votos": 0})

    def test_promedio_y_cantidad(self):
        for usuario, nota in zip(self.usuarios, (8, 5, 9)):
            Resena.objects.create(usuario=usuario, media=self.media, puntuacion=nota)

        resumen = resumen_puntuacion(self.media.pk)

        self.assertEqual(resumen["total_votos"], 3)
        self.assertEqual(resumen["promedio"], 7.33)

    def test_las_reseñas_ocultas_no_cuentan(self):
        Resena.objects.create(usuario=self.usuarios[0], media=self.media, puntuacion=10)
        Resena.objects.create(usuario=self.usuarios[1], media=self.media, puntuacion=2, oculta=True)

        self.assertEqual(resumen_puntuacion(self.media.pk), {"promedio": 10.0, "total_votos": 1})

    def test_no_mezcla_titulos(self):
        otra = Media.objects.create(titulo="B", tipo=Media.Tipo.SERIE)
        Resena.objects.create(usuario=self.usuarios[0], media=self.media, puntuacion=10)
        Resena.objects.create(usuario=self.usuarios[0], media=otra, puntuacion=2)

        self.assertEqual(resumen_puntuacion(self.media.pk)["promedio"], 10.0)
        self.assertEqual(resumen_puntuacion(otra.pk)["promedio"], 2.0)

    def test_anotacion_coincide_con_el_servicio(self):
        otra = Media.objects.create(titulo="B", tipo=Media.Tipo.SERIE)
        Resena.objects.create(usuario=self.usuarios[0], media=self.media, puntuacion=8)
        Resena.objects.create(usuario=self.usuarios[1], media=self.media, puntuacion=6)

        anotadas = {m.pk: m for m in anotar_puntuacion(Media.objects.all())}

        self.assertEqual(anotadas[self.media.pk].promedio_puntuacion, 7.0)
        self.assertEqual(anotadas[self.media.pk].total_votos, 2)
        self.assertIsNone(anotadas[otra.pk].promedio_puntuacion)
        self.assertEqual(anotadas[otra.pk].total_votos, 0)


class PromedioEnElCatalogoTests(APITestCase):
    def setUp(self):
        self.media = Media.objects.create(titulo="Con votos", tipo=Media.Tipo.PELICULA)
        self.sin_votos = Media.objects.create(titulo="Sin votos", tipo=Media.Tipo.PELICULA)
        self.usuarios = crear_usuarios(3)

    def test_la_ficha_muestra_promedio_y_votos(self):
        Resena.objects.create(usuario=self.usuarios[0], media=self.media, puntuacion=8)
        Resena.objects.create(usuario=self.usuarios[1], media=self.media, puntuacion=5)

        response = self.client.get(reverse("media-detail", kwargs={"pk": self.media.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["promedio_puntuacion"], 6.5)
        self.assertEqual(response.data["total_votos"], 2)

    def test_ficha_sin_votos(self):
        response = self.client.get(reverse("media-detail", kwargs={"pk": self.sin_votos.pk}))

        self.assertIsNone(response.data["promedio_puntuacion"])
        self.assertEqual(response.data["total_votos"], 0)

    def test_el_listado_tambien_trae_promedio(self):
        Resena.objects.create(usuario=self.usuarios[0], media=self.media, puntuacion=9)

        response = self.client.get(reverse("media-list"))

        por_titulo = {m["titulo"]: m for m in response.data["results"]}
        self.assertEqual(por_titulo["Con votos"]["promedio_puntuacion"], 9.0)
        self.assertEqual(por_titulo["Con votos"]["total_votos"], 1)
        self.assertEqual(por_titulo["Sin votos"]["total_votos"], 0)

    def test_el_promedio_se_actualiza_al_reseñar_y_al_editar(self):
        url_ficha = reverse("media-detail", kwargs={"pk": self.media.pk})
        url_resenas = reverse("media-resenas", kwargs={"media_id": self.media.pk})

        self.client.force_authenticate(self.usuarios[0])
        creada = self.client.post(url_resenas, {"puntuacion": 4})
        self.assertEqual(self.client.get(url_ficha).data["promedio_puntuacion"], 4.0)

        self.client.patch(reverse("resena-detail", kwargs={"pk": creada.data["id"]}), {"puntuacion": 10})
        self.assertEqual(self.client.get(url_ficha).data["promedio_puntuacion"], 10.0)

        self.client.delete(reverse("resena-detail", kwargs={"pk": creada.data["id"]}))
        self.assertEqual(self.client.get(url_ficha).data["total_votos"], 0)

    def test_filtrar_por_varios_generos_no_distorsiona_el_conteo(self):
        accion, drama = Genero.objects.create(nombre="Acción"), Genero.objects.create(nombre="Drama")
        self.media.generos.add(accion, drama)
        Resena.objects.create(usuario=self.usuarios[0], media=self.media, puntuacion=8)

        # "genero" coincide con un solo género, pero el JOIN con géneros no debe duplicar votos
        response = self.client.get(reverse("media-list"), {"genero": "accion"})

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["total_votos"], 1)
        self.assertEqual(response.data["results"][0]["promedio_puntuacion"], 8.0)

    def test_el_listado_no_hace_consultas_por_cada_titulo(self):
        for i in range(5):
            Media.objects.create(titulo=f"Extra {i}", tipo=Media.Tipo.PELICULA)

        with self.assertNumQueries(3):  # conteo + títulos + géneros (prefetch)
            self.client.get(reverse("media-list"))
