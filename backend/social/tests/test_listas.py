from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import ElementoLista, Lista

Usuario = get_user_model()


class ListasAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = Usuario.objects.create_user(
            username="lucia", email="lucia@example.com", password="Secur3Password!"
        )
        cls.user2 = Usuario.objects.create_user(
            username="carlos", email="carlos@example.com", password="Secur3Password!"
        )
        cls.media1 = Media.objects.create(
            titulo="Matrix", tipo=Media.Tipo.PELICULA
        )
        cls.media2 = Media.objects.create(
            titulo="Inception", tipo=Media.Tipo.PELICULA
        )
        cls.media3 = Media.objects.create(
            titulo="Interstellar", tipo=Media.Tipo.PELICULA
        )

        cls.lista_publica_user1 = Lista.objects.create(
            usuario=cls.user1,
            nombre="Ciencia Ficción",
            descripcion="Películas favoritas de ciencia ficción",
            tipo=Lista.Tipo.PERSONALIZADA,
            publica=True,
        )
        cls.lista_privada_user1 = Lista.objects.create(
            usuario=cls.user1,
            nombre="Secretos",
            descripcion="Lista privada",
            tipo=Lista.Tipo.PERSONALIZADA,
            publica=False,
        )
        cls.elemento1 = ElementoLista.objects.create(
            lista=cls.lista_publica_user1,
            media=cls.media1,
        )

    def test_crear_lista_autenticado_exito(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-list-create")
        data = {
            "nombre": "Joyas del Cine",
            "descripcion": "Mis favoritas absolutas",
            "tipo": "personalizada",
            "publica": True,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nombre"], "Joyas del Cine")
        self.assertEqual(response.data["usuario"], "lucia")
        self.assertEqual(response.data["total_elementos"], 0)

    def test_crear_lista_sin_sesion_da_401(self):
        url = reverse("lista-list-create")
        data = {"nombre": "No autorizada"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["codigo"], "not_authenticated")

    def test_no_se_puede_crear_duplicada_de_favoritas(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-list-create")
        self.client.post(url, {"nombre": "Favoritas 1", "tipo": "favoritas"})
        response = self.client.post(url, {"nombre": "Favoritas 2", "tipo": "favoritas"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_listar_listas_propias(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Como user1, ve tanto su lista pública como la privada
        nombres = [item["nombre"] for item in response.data.get("results", response.data)]
        self.assertIn("Ciencia Ficción", nombres)
        self.assertIn("Secretos", nombres)

    def test_listar_listas_otro_usuario_solo_muestra_publicas(self):
        # Visitante o carlos consultando las listas de lucia
        self.client.force_authenticate(self.user2)
        url = reverse("lista-list-create")
        response = self.client.get(url, {"usuario": "lucia"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data.get("results", response.data)
        nombres = [item["nombre"] for item in items]
        self.assertIn("Ciencia Ficción", nombres)
        self.assertNotIn("Secretos", nombres)

    def test_endpoint_usuario_listas(self):
        url = reverse("usuario-listas", args=["lucia"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data.get("results", response.data)
        nombres = [item["nombre"] for item in items]
        self.assertIn("Ciencia Ficción", nombres)
        self.assertNotIn("Secretos", nombres)


    def test_detalle_lista_publica_visible_para_todos(self):
        url = reverse("lista-detail", args=[self.lista_publica_user1.pk])
        # Visitante sin sesión
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre"], "Ciencia Ficción")
        self.assertEqual(len(response.data["elementos"]), 1)
        self.assertEqual(response.data["elementos"][0]["media_titulo"], "Matrix")

    def test_detalle_lista_privada_oculta_para_otros(self):
        url = reverse("lista-detail", args=[self.lista_privada_user1.pk])
        # Visitante
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Otro usuario autenticado
        self.client.force_authenticate(self.user2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Autor sí la puede ver
        self.client.force_authenticate(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_editar_lista_propia(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-detail", args=[self.lista_publica_user1.pk])
        response = self.client.patch(url, {"nombre": "Ciencia Ficción Épica"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre"], "Ciencia Ficción Épica")

    def test_editar_lista_ajena_prohibido(self):
        self.client.force_authenticate(self.user2)
        url = reverse("lista-detail", args=[self.lista_publica_user1.pk])
        response = self.client.patch(url, {"nombre": "Intento de hack"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["codigo"], "permission_denied")

    def test_borrar_lista_propia(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-detail", args=[self.lista_publica_user1.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lista.objects.filter(pk=self.lista_publica_user1.pk).exists())

    def test_borrar_lista_ajena_prohibido(self):
        self.client.force_authenticate(self.user2)
        url = reverse("lista-detail", args=[self.lista_publica_user1.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Lista.objects.filter(pk=self.lista_publica_user1.pk).exists())

    def test_agregar_elemento_a_lista_propia(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-elementos", args=[self.lista_publica_user1.pk])
        response = self.client.post(url, {"media_id": self.media2.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["media_titulo"], "Inception")
        self.assertEqual(self.lista_publica_user1.total_elementos, 2)

    def test_agregar_elemento_duplicado_da_error(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-elementos", args=[self.lista_publica_user1.pk])
        # media1 ya está en self.lista_publica_user1
        response = self.client.post(url, {"media_id": self.media1.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_agregar_elemento_a_lista_ajena_prohibido(self):
        self.client.force_authenticate(self.user2)
        url = reverse("lista-elementos", args=[self.lista_publica_user1.pk])
        response = self.client.post(url, {"media_id": self.media2.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["codigo"], "permission_denied")

    def test_quitar_elemento_de_lista(self):
        self.client.force_authenticate(self.user1)
        # Vía URL directa con media_id
        url = reverse("lista-elemento-detail", args=[self.lista_publica_user1.pk, self.media1.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.lista_publica_user1.total_elementos, 0)

    def test_quitar_elemento_de_lista_ajena_prohibido(self):
        self.client.force_authenticate(self.user2)
        url = reverse("lista-elemento-detail", args=[self.lista_publica_user1.pk, self.media1.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.lista_publica_user1.total_elementos, 1)

    def test_mis_listas_devuelve_todas_las_propias(self):
        self.client.force_authenticate(self.user1)

        response = self.client.get(reverse("usuarios-me-listas"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data.get("results", response.data)
        self.assertEqual(
            {item["nombre"] for item in items},
            {"Ciencia Ficción", "Secretos"},
        )

    def test_media_mis_listas_devuelve_estado_del_titulo(self):
        # Crear lista de favoritas para user1 y agregar media1
        fav = Lista.objects.create(
            usuario=self.user1, nombre="Favoritas", tipo=Lista.Tipo.FAVORITAS
        )
        ElementoLista.objects.create(lista=fav, media=self.media1)

        self.client.force_authenticate(self.user1)
        url = reverse("media-mis-listas", args=[self.media1.pk])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["media_id"], self.media1.pk)
        self.assertTrue(res.data["en_favoritas"])
        self.assertFalse(res.data["en_por_ver"])
        nombres = [l["nombre"] for l in res.data["listas"]]
        self.assertIn("Favoritas", nombres)
        self.assertIn("Ciencia Ficción", nombres)

    def test_media_mis_listas_sin_sesion_da_401(self):
        url = reverse("media-mis-listas", args=[self.media1.pk])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_mis_listas_exige_sesion(self):
        response = self.client.get(reverse("usuarios-me-listas"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_el_listado_no_hace_una_consulta_por_lista(self):
        for indice in range(5):
            Lista.objects.create(usuario=self.user1, nombre=f"Extra {indice}")
        self.client.force_authenticate(self.user1)

        with self.assertNumQueries(2):
            response = self.client.get(reverse("lista-list-create"))

        totales = {
            item["nombre"]: item["total_elementos"]
            for item in response.data["results"]
        }
        self.assertEqual(totales["Ciencia Ficción"], 1)
        self.assertEqual(totales["Extra 0"], 0)

    def test_elementos_de_lista_privada_ajena_dan_404(self):
        self.client.force_authenticate(self.user2)
        url = reverse("lista-elementos", args=[self.lista_privada_user1.pk])

        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.post(url, {"media_id": self.media2.pk}).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_modificar_elementos_sin_sesion_da_401(self):
        url = reverse("lista-elementos", args=[self.lista_publica_user1.pk])
        url_elemento = reverse(
            "lista-elemento-detail",
            args=[self.lista_publica_user1.pk, self.media1.pk],
        )

        agregar = self.client.post(url, {"media_id": self.media2.pk})
        quitar = self.client.delete(url_elemento)

        self.assertEqual(agregar.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(agregar.data["error"]["codigo"], "not_authenticated")
        self.assertEqual(quitar.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(
            ElementoLista.objects.filter(pk=self.elemento1.pk).exists()
        )


    def test_elementos_de_lista_publica_se_paginan(self):
        url = reverse("lista-elementos", args=[self.lista_publica_user1.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["media_id"], self.media1.pk)

    def test_quitar_titulo_con_identificador_invalido_devuelve_400(self):
        self.client.force_authenticate(self.user1)
        url = reverse("lista-elementos", args=[self.lista_publica_user1.pk])

        for valor in ("abc", "²", "0", "99999999999999999999"):
            with self.subTest(media_id=valor):
                response = self.client.delete(f"{url}?media_id={valor}")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("media_id", response.data["error"]["campos"])

        self.assertTrue(ElementoLista.objects.filter(pk=self.elemento1.pk).exists())

    def test_listas_del_sistema_conservan_tipo_y_no_se_eliminan(self):
        self.client.force_authenticate(self.user1)

        for tipo in (Lista.Tipo.FAVORITAS, Lista.Tipo.POR_VER):
            with self.subTest(tipo=tipo):
                lista = Lista.objects.create(usuario=self.user1, tipo=tipo, nombre=tipo.label)
                url = reverse("lista-detail", args=[lista.pk])

                response = self.client.patch(url, {"tipo": Lista.Tipo.PERSONALIZADA})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(self.client.delete(url).status_code, status.HTTP_400_BAD_REQUEST)
                lista.refresh_from_db()
                self.assertEqual(lista.tipo, tipo)
