from datetime import datetime, timezone

from django.test import TestCase

from cines.models import Cine, Funcion
from media.models import Media


class CineFuncionModelTests(TestCase):
    def test_cine_stores_location_and_website(self):
        cine = Cine.objects.create(
            nombre="Cine de prueba",
            ciudad="Valledupar",
            direccion="Centro comercial de prueba",
            sitio_web="https://example.com/",
        )

        self.assertEqual(str(cine), "Cine de prueba (Valledupar)")
        self.assertEqual(cine.sitio_web, "https://example.com/")

    def test_funcion_relates_cine_and_media_and_tracks_update_time(self):
        cine = Cine.objects.create(
            nombre="Cine de prueba",
            ciudad="Valledupar",
            direccion="Centro comercial de prueba",
        )
        media = Media.objects.create(titulo="Película de prueba", tipo="pelicula")
        fecha_hora = datetime(2026, 10, 15, 19, 30, tzinfo=timezone.utc)

        funcion = Funcion.objects.create(
            cine=cine,
            media=media,
            fecha_hora=fecha_hora,
            sala="Sala 1",
            formato="3D subtitulada",
            fuente_scraping="https://example.com/cartelera/",
        )

        self.assertEqual(funcion.cine, cine)
        self.assertEqual(funcion.media, media)
        self.assertEqual(funcion.fecha_hora, fecha_hora)
        self.assertEqual(funcion.sala, "Sala 1")
        self.assertEqual(funcion.formato, "3D subtitulada")
        self.assertEqual(funcion.fuente_scraping, "https://example.com/cartelera/")
        self.assertIsNotNone(funcion.fecha_actualizacion)
        self.assertEqual(media.funciones.get(), funcion)
        self.assertEqual(cine.funciones.get(), funcion)
