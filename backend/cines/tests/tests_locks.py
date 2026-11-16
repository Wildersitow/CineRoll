from unittest.mock import MagicMock, patch

import redis
from django.test import SimpleTestCase

from cines.locks import candado_scraping


def _cliente_con(candado):
    cliente = MagicMock()
    cliente.lock.return_value = candado
    return cliente


class CandadoScrapingTests(SimpleTestCase):
    def test_toma_y_libera_el_candado(self):
        candado = MagicMock()
        candado.acquire.return_value = True

        with patch("cines.locks._cliente", return_value=_cliente_con(candado)) as c:
            with candado_scraping("cinepolis", "valledupar", 420) as libre:
                self.assertTrue(libre)
                candado.release.assert_not_called()

        c.return_value.lock.assert_called_once_with(
            "cartelera:candado:cinepolis:valledupar", timeout=420
        )
        candado.acquire.assert_called_once_with(blocking=False)
        candado.release.assert_called_once()

    def test_si_esta_ocupado_no_espera_ni_libera(self):
        candado = MagicMock()
        candado.acquire.return_value = False

        with patch("cines.locks._cliente", return_value=_cliente_con(candado)):
            with candado_scraping("cinepolis", "valledupar", 420) as libre:
                self.assertFalse(libre)

        candado.release.assert_not_called()

    def test_libera_el_candado_aunque_el_cuerpo_falle(self):
        candado = MagicMock()
        candado.acquire.return_value = True

        with patch("cines.locks._cliente", return_value=_cliente_con(candado)):
            with self.assertRaises(RuntimeError):
                with candado_scraping("cinepolis", "valledupar", 420):
                    raise RuntimeError("fallo del scraper")

        candado.release.assert_called_once()

    def test_si_redis_falla_continua_sin_candado(self):
        cliente = MagicMock()
        cliente.lock.side_effect = redis.exceptions.ConnectionError("sin Redis")

        with patch("cines.locks._cliente", return_value=cliente):
            with self.assertLogs("cines.locks", level="WARNING"):
                with candado_scraping("cinepolis", "valledupar", 420) as libre:
                    self.assertTrue(libre)

    def test_un_candado_expirado_no_rompe_la_liberacion(self):
        candado = MagicMock()
        candado.acquire.return_value = True
        candado.release.side_effect = redis.exceptions.LockError("expiró")

        with patch("cines.locks._cliente", return_value=_cliente_con(candado)):
            with self.assertLogs("cines.locks", level="WARNING"):
                with candado_scraping("cinepolis", "valledupar", 420) as libre:
                    self.assertTrue(libre)