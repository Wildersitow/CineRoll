import uuid
from unittest import mock

from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social import chats
from social.models import Mensaje
from usuarios.models import Usuario


class BaseChat(APITestCase):
    def setUp(self):
        self.valeria = Usuario.objects.create_user(
            username="valeria", email="valeria@example.com", password="Passw0rd-2026!",
            first_name="Valeria", last_name="Torres", avatar="https://img.example.com/v.png",
        )
        self.sergio = Usuario.objects.create_user(
            username="sergio", email="sergio@example.com", password="Passw0rd-2026!"
        )
        self.ana = Usuario.objects.create_user(
            username="ana", email="ana@example.com", password="Passw0rd-2026!"
        )
        self.media = Media.objects.create(
            titulo="Dune", tipo=Media.Tipo.PELICULA, estado=Media.Estado.EN_CARTELERA
        )

    def privado(self, username):
        return reverse("chat-privado", kwargs={"username": username})

    def sala(self, media_id=None):
        return reverse("chat-sala-media", kwargs={"media_id": media_id or self.media.pk})


class ChatPrivadoTests(BaseChat):
    def test_requiere_sesion(self):
        self.assertEqual(self.client.get(self.privado("sergio")).status_code, status.HTTP_401_UNAUTHORIZED)
        respuesta = self.client.post(self.privado("sergio"), {"texto": "hola"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_enviar_y_leer_conversacion(self):
        self.client.force_authenticate(self.valeria)
        respuesta = self.client.post(self.privado("sergio"), {"texto": "  ¿Vamos a Dune?  "}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["texto"], "¿Vamos a Dune?")
        self.assertEqual(respuesta.data["autor"], "valeria")
        self.assertEqual(respuesta.data["autor_avatar"], "https://img.example.com/v.png")

        self.client.force_authenticate(self.sergio)
        self.client.post(self.privado("valeria"), {"texto": "¡Claro!"}, format="json")
        datos = self.client.get(self.privado("valeria")).data
        self.assertEqual([m["texto"] for m in datos["results"]], ["¿Vamos a Dune?", "¡Claro!"])
        self.assertFalse(datos["hay_anteriores"])
        self.assertFalse(datos["hay_mas"])

    def test_terceros_no_ven_la_conversacion(self):
        Mensaje.objects.create(autor=self.valeria, destinatario=self.sergio, texto="secreto")
        self.client.force_authenticate(self.ana)
        datos = self.client.get(self.privado("valeria")).data
        self.assertEqual(datos["results"], [])

    def test_no_puede_escribirse_a_si_mismo(self):
        self.client.force_authenticate(self.valeria)
        respuesta = self.client.post(self.privado("valeria"), {"texto": "hola"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", respuesta.data)

    def test_usuario_inexistente_o_inactivo(self):
        self.client.force_authenticate(self.valeria)
        self.assertEqual(self.client.get(self.privado("nadie")).status_code, status.HTTP_404_NOT_FOUND)
        self.ana.is_active = False
        self.ana.save()
        self.assertEqual(self.client.get(self.privado("ana")).status_code, status.HTTP_404_NOT_FOUND)

    def test_texto_vacio_o_muy_largo(self):
        self.client.force_authenticate(self.valeria)
        for texto in ("   ", "x" * 2001):
            respuesta = self.client.post(self.privado("sergio"), {"texto": texto}, format="json")
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Mensaje.objects.exists())

    def test_envio_repetido_no_duplica(self):
        self.client.force_authenticate(self.valeria)
        envio = str(uuid.uuid4())
        primera = self.client.post(self.privado("sergio"), {"texto": "hola", "envio": envio}, format="json")
        segunda = self.client.post(self.privado("sergio"), {"texto": "hola", "envio": envio}, format="json")
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertEqual(primera.data["id"], segunda.data["id"])
        self.assertEqual(Mensaje.objects.count(), 1)

    def test_envio_simultaneo_devuelve_el_existente(self):
        self.client.force_authenticate(self.valeria)
        envio = uuid.uuid4()
        existente = Mensaje.objects.create(
            autor=self.valeria, destinatario=self.sergio, texto="hola", envio=envio
        )
        # Simula la carrera: la búsqueda previa no lo ve y el INSERT choca.
        with mock.patch.object(chats.Mensaje.objects, "create", side_effect=IntegrityError):
            with mock.patch("social.chats.Mensaje.objects.filter") as filtro:
                filtro.return_value.first.return_value = None
                respuesta = self.client.post(
                    self.privado("sergio"), {"texto": "hola", "envio": str(envio)}, format="json"
                )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["id"], existente.pk)


class PaginacionTests(BaseChat):
    def setUp(self):
        super().setUp()
        self.mensajes = Mensaje.objects.bulk_create(
            [Mensaje(autor=self.valeria, media=self.media, texto=f"m{i}") for i in range(chats.POR_PAGINA + 10)]
        )
        self.ids = list(Mensaje.objects.order_by("id").values_list("id", flat=True))

    def test_primera_pagina_trae_los_ultimos(self):
        datos = self.client.get(self.sala()).data
        self.assertEqual([m["id"] for m in datos["results"]], self.ids[-chats.POR_PAGINA:])
        self.assertTrue(datos["hay_anteriores"])
        self.assertFalse(datos["hay_mas"])

    def test_antes_trae_los_anteriores(self):
        primero_visible = self.ids[-chats.POR_PAGINA]
        datos = self.client.get(self.sala(), {"antes": primero_visible}).data
        self.assertEqual([m["id"] for m in datos["results"]], self.ids[:10])
        self.assertFalse(datos["hay_anteriores"])

    def test_despues_trae_lo_nuevo_por_tandas(self):
        datos = self.client.get(self.sala(), {"despues": self.ids[4]}).data
        self.assertEqual([m["id"] for m in datos["results"]], self.ids[5:5 + chats.POR_PAGINA])
        self.assertTrue(datos["hay_mas"])
        self.assertTrue(datos["hay_anteriores"])
        datos = self.client.get(self.sala(), {"despues": self.ids[-1]}).data
        self.assertEqual(datos["results"], [])
        self.assertFalse(datos["hay_mas"])

    def test_cursor_invalido(self):
        for valor in ("abc", "-3"):
            respuesta = self.client.get(self.sala(), {"despues": valor})
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class SalaMediaTests(BaseChat):
    def test_lectura_publica_y_escritura_con_sesion(self):
        Mensaje.objects.create(autor=self.sergio, media=self.media, texto="Gran película")
        self.assertEqual(self.client.get(self.sala()).data["results"][0]["texto"], "Gran película")
        respuesta = self.client.post(self.sala(), {"texto": "hola"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.valeria)
        respuesta = self.client.post(self.sala(), {"texto": "¡Totalmente!"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Mensaje.objects.get(pk=respuesta.data["id"]).media, self.media)

    def test_sala_de_titulo_inexistente(self):
        self.assertEqual(self.client.get(self.sala(999999)).status_code, status.HTTP_404_NOT_FOUND)

    def test_sala_no_mezcla_mensajes_privados(self):
        Mensaje.objects.create(autor=self.valeria, destinatario=self.sergio, texto="privado")
        self.assertEqual(self.client.get(self.sala()).data["results"], [])


class BandejaTests(BaseChat):
    url = reverse("chats-bandeja")

    def test_requiere_sesion(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_una_fila_por_persona_mas_reciente_primero(self):
        Mensaje.objects.create(autor=self.valeria, destinatario=self.sergio, texto="hola sergio")
        Mensaje.objects.create(autor=self.ana, destinatario=self.sergio, texto="hola, soy ana")
        Mensaje.objects.create(autor=self.sergio, destinatario=self.valeria, texto="¡hola valeria!")
        Mensaje.objects.create(autor=self.valeria, media=self.media, texto="en la sala")

        self.client.force_authenticate(self.sergio)
        filas = self.client.get(self.url).data
        self.assertEqual([f["usuario"] for f in filas], ["valeria", "ana"])
        self.assertEqual(filas[0]["nombre"], "Valeria Torres")
        self.assertEqual(filas[0]["avatar"], "https://img.example.com/v.png")
        self.assertEqual(filas[0]["ultimo_mensaje"]["texto"], "¡hola valeria!")
        self.assertTrue(filas[0]["ultimo_mensaje"]["mio"])
        self.assertFalse(filas[1]["ultimo_mensaje"]["mio"])

    def test_bandeja_vacia(self):
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.client.get(self.url).data, [])


class MensajeModeloTests(BaseChat):
    def test_debe_tener_un_solo_destino(self):
        with self.assertRaises(IntegrityError):
            Mensaje.objects.create(
                autor=self.valeria, destinatario=self.sergio, media=self.media, texto="x"
            )

    def test_sin_destino_falla(self):
        with self.assertRaises(IntegrityError):
            Mensaje.objects.create(autor=self.valeria, texto="x")
