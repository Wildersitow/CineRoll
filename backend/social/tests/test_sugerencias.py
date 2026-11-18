from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import SugerenciaEdicion
from usuarios.models import Usuario


class SugerenciasEdicionApiTests(APITestCase):
    def setUp(self):
        self.media = Media.objects.create(
            titulo="Título original",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.EN_CARTELERA,
        )
        self.usuario = Usuario.objects.create_user(
            username="lector", email="lector@example.com", password="x"
        )
        self.admin = Usuario.objects.create_superuser(
            username="admin", email="admin@example.com", password="x"
        )
        self.url = reverse("media-sugerencias", kwargs={"media_id": self.media.pk})

    def test_visitante_no_puede_crear_sugerencia(self):
        response = self.client.post(
            self.url,
            {"campo": "sinopsis", "valor_propuesto": "Nueva sinopsis"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_crea_solo_campos_permitidos(self):
        self.client.force_authenticate(self.usuario)

        response = self.client.post(
            self.url,
            {"campo": "sinopsis", "valor_propuesto": "Nueva sinopsis", "motivo": "Corrección"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sugerencia = SugerenciaEdicion.objects.get()
        self.assertEqual(sugerencia.usuario, self.usuario)
        self.assertEqual(sugerencia.media, self.media)
        self.assertEqual(sugerencia.estado, SugerenciaEdicion.Estado.PENDIENTE)

        rechazada = self.client.post(
            self.url,
            {"campo": "estado", "valor_propuesto": "fuera_cartelera"},
            format="json",
        )
        self.assertEqual(rechazada.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campo", rechazada.data["error"]["campos"])

    def test_admin_aprueba_y_aplica_sugerencia(self):
        sugerencia = SugerenciaEdicion.objects.create(
            usuario=self.usuario,
            media=self.media,
            campo="sinopsis",
            valor_propuesto="Sinopsis aprobada",
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("sugerencia-aprobar", kwargs={"pk": sugerencia.pk}),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sugerencia.refresh_from_db()
        self.media.refresh_from_db()
        self.assertEqual(sugerencia.estado, SugerenciaEdicion.Estado.APROBADA)
        self.assertEqual(sugerencia.revisado_por, self.admin)
        self.assertEqual(self.media.sinopsis, "Sinopsis aprobada")

    def test_admin_rechaza_sugerencia(self):
        sugerencia = SugerenciaEdicion.objects.create(
            usuario=self.usuario,
            media=self.media,
            campo="titulo",
            valor_propuesto="Título corregido",
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("sugerencia-rechazar", kwargs={"pk": sugerencia.pk}),
            {"motivo_rechazo": "No coincide con la ficha oficial"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sugerencia.refresh_from_db()
        self.media.refresh_from_db()
        self.assertEqual(sugerencia.estado, SugerenciaEdicion.Estado.RECHAZADA)
        self.assertEqual(sugerencia.motivo_rechazo, "No coincide con la ficha oficial")
        self.assertEqual(self.media.titulo, "Título original")

    def test_usuario_no_ve_sugerencias_de_otro_usuario(self):
        otro = Usuario.objects.create_user(username="otro", password="x")
        SugerenciaEdicion.objects.create(
            usuario=otro,
            media=self.media,
            campo="trailer_url",
            valor_propuesto="https://youtube.com/watch?v=ejemplo",
        )
        self.client.force_authenticate(self.usuario)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
