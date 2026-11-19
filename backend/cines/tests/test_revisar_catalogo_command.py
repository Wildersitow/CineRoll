import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from cines.models import TituloPendiente
from media.models import Genero, Media, Persona, Credito


class RevisarCatalogoCommandTests(TestCase):
    def setUp(self):
        self.incompleta = Media.objects.create(
            titulo="Ficha incompleta",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.EN_CARTELERA,
        )

        self.completa = Media.objects.create(
            titulo="Ficha completa",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.PROXIMO_ESTRENO,
            sinopsis="Sinopsis disponible",
            poster_url="https://example.com/poster.jpg",
            trailer_url="https://example.com/trailer",
        )
        genero = Genero.objects.create(nombre="Drama")
        persona = Persona.objects.create(nombre="Actriz prueba")
        self.completa.generos.add(genero)
        Credito.objects.create(
            media=self.completa,
            persona=persona,
            rol=Credito.Rol.ACTOR,
        )

        self.pendiente = TituloPendiente.objects.create(
            titulo_original="Título desconocido",
            titulo_normalizado="titulo desconocido",
            cine_nombre="Cine prueba",
            ciudad="Valledupar",
            estado=TituloPendiente.Estado.PENDIENTE,
        )

    def test_lista_fichas_incompletas_y_pendientes(self):
        salida = StringIO()

        call_command("revisar_catalogo", stdout=salida)
        texto = salida.getvalue()

        self.assertIn("Ficha incompleta", texto)
        self.assertIn("sinopsis", texto)
        self.assertIn("poster", texto)
        self.assertIn("trailer", texto)
        self.assertIn("generos", texto)
        self.assertIn("reparto", texto)
        self.assertNotIn("Ficha completa", texto)
        self.assertIn("Título desconocido", texto)

    def test_json_incluye_campos_faltantes_y_pendientes(self):
        salida = StringIO()

        call_command("revisar_catalogo", json=True, stdout=salida)
        informe = json.loads(salida.getvalue())

        self.assertEqual(len(informe["fichas_incompletas"]), 1)
        ficha = informe["fichas_incompletas"][0]
        self.assertEqual(ficha["id"], self.incompleta.pk)
        self.assertEqual(
            set(ficha["campos_faltantes"]),
            {"sinopsis", "poster", "trailer", "generos", "reparto"},
        )
        self.assertEqual(len(informe["titulos_pendientes"]), 1)
        self.assertEqual(
            informe["titulos_pendientes"][0]["id"],
            self.pendiente.pk,
        )

    def test_no_lista_pendiente_resuelto(self):
        self.pendiente.estado = TituloPendiente.Estado.RESUELTO
        self.pendiente.media_asociada = self.completa
        self.pendiente.save(update_fields=["estado", "media_asociada"])

        salida = StringIO()
        call_command("revisar_catalogo", json=True, stdout=salida)
        informe = json.loads(salida.getvalue())

        self.assertEqual(informe["titulos_pendientes"], [])
