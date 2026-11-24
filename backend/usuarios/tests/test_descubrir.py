from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import Resena, Seguimiento

Usuario = get_user_model()


class BaseDescubrir(APITestCase):
    def setUp(self):
        crear = Usuario.objects.create_user
        self.yo = crear(username="valeria", email="v@example.com", password="Passw0rd-2026!")
        self.sergio = crear(username="sergio", email="s@example.com", password="x", first_name="Sergio", last_name="Díaz")
        self.ana = crear(username="ana_cine", email="a@example.com", password="x", first_name="Ana", last_name="Mejía")
        self.diana = crear(username="diana", email="d@example.com", password="x", first_name="Diana")
        self.inactivo = crear(username="sergio_viejo", email="i@example.com", password="x", is_active=False)
        media = Media.objects.create(titulo="Dune", tipo=Media.Tipo.PELICULA)
        Resena.objects.create(usuario=self.diana, media=media, puntuacion=8)


class BuscarUsuariosTests(BaseDescubrir):
    url = reverse("usuarios_buscar")

    def nombres(self, respuesta):
        return [u["username"] for u in respuesta.data["results"]]

    def test_busca_por_usuario_nombre_y_apellido(self):
        self.assertEqual(self.nombres(self.client.get(self.url, {"search": "serg"})), ["sergio"])
        self.assertEqual(self.nombres(self.client.get(self.url, {"search": "Mejía"})), ["ana_cine"])
        self.assertEqual(self.nombres(self.client.get(self.url, {"search": "@ana"})), ["ana_cine", "diana"])

    def test_texto_muy_corto_no_devuelve_nada(self):
        respuesta = self.client.get(self.url, {"search": "a"})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["results"], [])
        self.assertEqual(self.client.get(self.url).data["results"], [])

    def test_coincidencia_exacta_primero(self):
        Seguimiento.objects.create(seguidor=self.yo, seguido=self.ana)
        Usuario.objects.create_user(username="diana_fan", email="f@example.com", password="x")
        Seguimiento.objects.create(seguidor=self.ana, seguido=Usuario.objects.get(username="diana_fan"))
        self.assertEqual(self.nombres(self.client.get(self.url, {"search": "diana"}))[0], "diana")

    def test_resumen_y_lo_sigo(self):
        Seguimiento.objects.create(seguidor=self.yo, seguido=self.diana)
        anonimo = self.client.get(self.url, {"search": "diana"}).data["results"][0]
        self.assertEqual(anonimo["total_resenas"], 1)
        self.assertEqual(anonimo["total_seguidores"], 1)
        self.assertIsNone(anonimo["lo_sigo"])
        self.client.force_authenticate(self.yo)
        self.assertTrue(self.client.get(self.url, {"search": "diana"}).data["results"][0]["lo_sigo"])


class UsuariosRecomendadosTests(BaseDescubrir):
    url = reverse("usuarios_recomendados")

    def nombres(self):
        return [u["username"] for u in self.client.get(self.url).data]

    def test_sin_sesion_muestra_activos_sin_inactivos(self):
        nombres = self.nombres()
        self.assertEqual(nombres[0], "diana")
        self.assertNotIn("sergio_viejo", nombres)

    def test_excluye_a_mi_y_a_quien_ya_sigo_y_prioriza_en_comun(self):
        Seguimiento.objects.create(seguidor=self.yo, seguido=self.sergio)
        Seguimiento.objects.create(seguidor=self.sergio, seguido=self.ana)
        self.client.force_authenticate(self.yo)
        datos = self.client.get(self.url).data
        nombres = [u["username"] for u in datos]
        self.assertNotIn("valeria", nombres)
        self.assertNotIn("sergio", nombres)
        self.assertEqual(nombres[0], "ana_cine")
        self.assertEqual(datos[0]["en_comun"], 1)
        self.assertFalse(datos[0]["lo_sigo"])

    def test_limite(self):
        for i in range(12):
            Usuario.objects.create_user(username=f"extra{i}", email=f"e{i}@example.com", password="x")
        self.assertEqual(len(self.nombres()), 8)
