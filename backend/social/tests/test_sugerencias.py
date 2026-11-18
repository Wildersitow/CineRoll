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

    def test_no_permite_valor_igual_al_actual(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.post(
            self.url,
            {"campo": "titulo", "valor_propuesto": "Título original"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("valor_propuesto", response.data["error"]["campos"])

    def test_reutiliza_validaciones_de_media(self):
        self.client.force_authenticate(self.usuario)

        duracion = self.client.post(
            self.url,
            {"campo": "duracion", "valor_propuesto": 0},
            format="json",
        )
        self.assertEqual(duracion.status_code, status.HTTP_400_BAD_REQUEST)

        fecha = self.client.post(
            self.url,
            {"campo": "fecha_estreno", "valor_propuesto": "fecha-invalida"},
            format="json",
        )
        self.assertEqual(fecha.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_permite_dos_sugerencias_pendientes_del_mismo_usuario_titulo_y_campo(self):
        self.client.force_authenticate(self.usuario)
        primera = self.client.post(
            self.url,
            {"campo": "sinopsis", "valor_propuesto": "Primera sinopsis"},
            format="json",
        )
        repetida = self.client.post(
            self.url,
            {"campo": "sinopsis", "valor_propuesto": "Otra sinopsis"},
            format="json",
        )
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(repetida.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SugerenciaEdicion.objects.count(), 1)

    def test_listado_propio_esta_paginado_filtra_estado_y_oculta_otras(self):
        otra = Usuario.objects.create_user(username="otra", password="x")
        propia = SugerenciaEdicion.objects.create(
            usuario=self.usuario,
            media=self.media,
            campo="sinopsis",
            valor_propuesto="Sinopsis propia",
        )
        SugerenciaEdicion.objects.create(
            usuario=otra,
            media=self.media,
            campo="titulo",
            valor_propuesto="Título ajeno",
        )
        propia.estado = SugerenciaEdicion.Estado.RECHAZADA
        propia.motivo_rechazo = "Fuente insuficiente"
        propia.save(update_fields=["estado", "motivo_rechazo"])

        self.client.force_authenticate(self.usuario)
        response = self.client.get("/api/usuarios/me/sugerencias/?estado=rechazada")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["motivo_rechazo"], "Fuente insuficiente")

    def test_aprobacion_guarda_valor_anterior_y_no_se_puede_aprobar_dos_veces(self):
        sugerencia = SugerenciaEdicion.objects.create(
            usuario=self.usuario,
            media=self.media,
            campo="titulo",
            valor_propuesto="Título aprobado",
        )
        self.client.force_authenticate(self.admin)

        aprobada = self.client.post(
            reverse("sugerencia-aprobar", kwargs={"pk": sugerencia.pk}),
            format="json",
        )
        repetida = self.client.post(
            reverse("sugerencia-aprobar", kwargs={"pk": sugerencia.pk}),
            format="json",
        )

        self.assertEqual(aprobada.status_code, status.HTTP_200_OK)
        self.assertEqual(repetida.status_code, status.HTTP_400_BAD_REQUEST)
        sugerencia.refresh_from_db()
        self.media.refresh_from_db()
        self.assertEqual(sugerencia.valor_anterior, "Título original")
        self.assertEqual(self.media.titulo, "Título aprobado")

    def test_rechazo_exige_motivo_y_resolucion_impide_segundo_rechazo(self):
        sugerencia = SugerenciaEdicion.objects.create(
            usuario=self.usuario,
            media=self.media,
            campo="sinopsis",
            valor_propuesto="Sinopsis propuesta",
        )
        self.client.force_authenticate(self.admin)

        sin_motivo = self.client.post(
            reverse("sugerencia-rechazar", kwargs={"pk": sugerencia.pk}),
            {"motivo_rechazo": "  "},
            format="json",
        )
        rechazada = self.client.post(
            reverse("sugerencia-rechazar", kwargs={"pk": sugerencia.pk}),
            {"motivo_rechazo": "No coincide con la ficha oficial"},
            format="json",
        )
        segunda_resolucion = self.client.post(
            reverse("sugerencia-rechazar", kwargs={"pk": sugerencia.pk}),
            {"motivo_rechazo": "Intento duplicado"},
            format="json",
        )

        self.assertEqual(rechazada.status_code, status.HTTP_200_OK)
        self.assertEqual(sin_motivo.status_code, status.HTTP_400_BAD_REQUEST)
        sugerencia.refresh_from_db()
        self.assertEqual(sugerencia.estado, SugerenciaEdicion.Estado.RECHAZADA)
        self.assertEqual(sugerencia.motivo_rechazo, "No coincide con la ficha oficial")
