import json
from unittest.mock import patch

from django.test import TestCase

from cines.models import Cine, Funcion
from cines.services import CarteleraScrapeResult
from cines.tasks import limpiar_cartelera_vencida, scrape_cartelera_task
from media.models import Media


def _resultado(**cambios):
    datos = dict(
        cine="cinepolis",
        ciudad="valledupar",
        funciones_leidas=10,
        funciones_asociadas=8,
        funciones_creadas=3,
        funciones_actualizadas=5,
        titulos_pendientes=2,
        peliculas_en_cartelera=1,
        estrenos_leidos=0,
        estrenos_asociados=0,
        funciones_vencidas_eliminadas=4,
        peliculas_fuera_cartelera=0,
        estrenos_sin_coincidencia=(),
        titulos_pendientes_mostrar=("#1 Película — Cine (valledupar)",),
    )
    datos.update(cambios)
    return CarteleraScrapeResult(**datos)


class ScrapeCarteleraTaskTests(TestCase):
    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_la_tarea_solo_delega_en_el_servicio(self, servicio):
        servicio.return_value = _resultado()

        resultado = scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        servicio.assert_called_once_with(
            cinema_provider="cinepolis", city_slug="valledupar"
        )
        self.assertEqual(resultado["cine"], "cinepolis")
        self.assertEqual(resultado["funciones_leidas"], 10)
        self.assertEqual(resultado["funciones_creadas"], 3)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_el_resultado_se_puede_serializar_en_json(self, servicio):
        servicio.return_value = _resultado()

        resultado = scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        json.dumps(resultado)  # Celery lo exige para guardarlo en Redis


class LimpiarCarteleraVencidaTaskTests(TestCase):
    def test_borra_funciones_vencidas_y_saca_de_cartelera(self):
        media = Media.objects.create(
            titulo="Solo funciones pasadas",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.EN_CARTELERA,
        )
        cine = Cine.objects.create(nombre="Cine A", ciudad="valledupar")
        from datetime import timedelta

        from django.utils import timezone

        Funcion.objects.create(
            cine=cine, media=media, fecha_hora=timezone.now() - timedelta(hours=1)
        )

        resultado = limpiar_cartelera_vencida.apply().get()

        self.assertEqual(resultado["funciones_vencidas_eliminadas"], 1)
        self.assertEqual(resultado["peliculas_fuera_cartelera"], 1)
        self.assertFalse(Funcion.objects.exists())
        media.refresh_from_db()
        self.assertEqual(media.estado, Media.Estado.FUERA_CARTELERA)