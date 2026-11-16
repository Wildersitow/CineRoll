from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from media.models import Media
from social.models import ElementoLista, Lista, Seguimiento, SugerenciaEdicion

Usuario = get_user_model()


class ModelosSocialesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = Usuario.objects.create_user(
            username="lucia", email="lucia@example.com", password="Password123!"
        )
        cls.user2 = Usuario.objects.create_user(
            username="carlos", email="carlos@example.com", password="Password123!"
        )
        cls.media1 = Media.objects.create(
            titulo="Inception", tipo=Media.Tipo.PELICULA
        )
        cls.media2 = Media.objects.create(
            titulo="Interstellar", tipo=Media.Tipo.PELICULA
        )

    def test_crear_lista_y_str(self):
        lista = Lista.objects.create(
            usuario=self.user1,
            nombre="Ciencia Ficción Favorita",
            descripcion="Mis películas favoritas del espacio",
            tipo=Lista.Tipo.PERSONALIZADA,
            publica=True,
        )
        self.assertEqual(str(lista), f"{lista.nombre} ({self.user1})")
        self.assertEqual(lista.total_elementos, 0)

    def test_restriccion_lista_sistema_unica_por_usuario(self):
        Lista.objects.create(
            usuario=self.user1,
            nombre="Mis Favoritas",
            tipo=Lista.Tipo.FAVORITAS,
        )
        # Intentar crear otra lista de favoritas para el mismo usuario debe fallar
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Lista.objects.create(
                    usuario=self.user1,
                    nombre="Otras Favoritas",
                    tipo=Lista.Tipo.FAVORITAS,
                )

        # Pero otro usuario sí puede tener su propia lista de favoritas
        lista_carlos = Lista.objects.create(
            usuario=self.user2,
            nombre="Favoritas de Carlos",
            tipo=Lista.Tipo.FAVORITAS,
        )
        self.assertIsNotNone(lista_carlos.pk)

    def test_elemento_lista_creacion_y_unicidad(self):
        lista = Lista.objects.create(
            usuario=self.user1,
            nombre="Por Ver",
            tipo=Lista.Tipo.POR_VER,
        )
        elemento = ElementoLista.objects.create(
            lista=lista,
            media=self.media1,
            orden=1,
        )
        self.assertEqual(str(elemento), f"{self.media1} en {lista}")
        self.assertEqual(lista.total_elementos, 1)

        # No se puede repetir la misma media en la misma lista
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ElementoLista.objects.create(
                    lista=lista,
                    media=self.media1,
                    orden=2,
                )

    def test_seguimiento_creacion_y_restricciones(self):
        seguimiento = Seguimiento.objects.create(
            seguidor=self.user1,
            seguido=self.user2,
        )
        self.assertEqual(str(seguimiento), f"{self.user1} sigue a {self.user2}")

        # No se puede seguir dos veces al mismo usuario
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Seguimiento.objects.create(
                    seguidor=self.user1,
                    seguido=self.user2,
                )

        # Un usuario no puede seguirse a sí mismo
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Seguimiento.objects.create(
                    seguidor=self.user1,
                    seguido=self.user1,
                )

    def test_sugerencia_edicion_creacion_y_str(self):
        sugerencia = SugerenciaEdicion.objects.create(
            usuario=self.user1,
            media=self.media1,
            campo="sinopsis",
            valor_propuesto="Una nueva sinopsis más detallada para Inception.",
            motivo="La actual es demasiado corta.",
        )
        self.assertEqual(
            str(sugerencia),
            f"Sugerencia de {self.user1} sobre {self.media1} (sinopsis)",
        )
        self.assertEqual(sugerencia.estado, SugerenciaEdicion.Estado.PENDIENTE)

