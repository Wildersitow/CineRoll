from contextlib import contextmanager
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from cines.models import EjecucionScraping
from cines.services import CarteleraScrapeResult, ScraperError
from backend.usuarios.tasks import scrape_cartelera_task
from usuarios.models import Usuario


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
        titulos_pendientes_mostrar=(),
        funciones_obsoletas_eliminadas=6,
    )
    datos.update(cambios)
    return CarteleraScrapeResult(**datos)


def _candado_falso(libre):
    @contextmanager
    def candado(cine, ciudad, timeout):
        yield libre

    return candado


class RegistroDeEjecucionesTests(TestCase):
    def setUp(self):
        parche = patch("cines.tasks.candado_scraping", _candado_falso(True))
        parche.start()
        self.addCleanup(parche.stop)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_una_ejecucion_exitosa_guarda_los_conteos(self, servicio):
        servicio.return_value = _resultado()

        scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        ejecucion = EjecucionScraping.objects.get()
        self.assertEqual(ejecucion.cine, "cinepolis")
        self.assertEqual(ejecucion.ciudad, "valledupar")
        self.assertEqual(ejecucion.estado, EjecucionScraping.Estado.EXITOSA)
        self.assertEqual(ejecucion.intento, 1)
        self.assertEqual(ejecucion.funciones_leidas, 10)
        self.assertEqual(ejecucion.funciones_creadas, 3)
        self.assertEqual(ejecucion.funciones_obsoletas_eliminadas, 6)
        self.assertEqual(ejecucion.mensaje_error, "")
        self.assertIsNotNone(ejecucion.fin)
        self.assertIsNotNone(ejecucion.duracion)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_cada_intento_fallido_queda_registrado_con_su_error(self, servicio):
        servicio.side_effect = ScraperError("el sitio no responde")

        scrape_cartelera_task.apply(args=("cinepolis", "valledupar"))

        ejecuciones = EjecucionScraping.objects.order_by("intento")
        self.assertEqual(ejecuciones.count(), 4)  # 1 intento + 3 reintentos
        self.assertEqual(
            set(ejecuciones.values_list("estado", flat=True)),
            {EjecucionScraping.Estado.FALLIDA},
        )
        self.assertEqual([e.intento for e in ejecuciones], [1, 2, 3, 4])
        self.assertIn("el sitio no responde", ejecuciones[0].mensaje_error)
        self.assertIn("ScraperError", ejecuciones[0].mensaje_error)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_un_reintento_exitoso_deja_una_fallida_y_una_exitosa(self, servicio):
        servicio.side_effect = [ScraperError("falla temporal"), _resultado()]

        scrape_cartelera_task.apply(args=("cinepolis", "valledupar"))

        estados = list(
            EjecucionScraping.objects.order_by("intento").values_list(
                "estado", flat=True
            )
        )
        self.assertEqual(
            estados,
            [EjecucionScraping.Estado.FALLIDA, EjecucionScraping.Estado.EXITOSA],
        )

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_un_error_de_configuracion_se_registra_sin_reintentar(self, servicio):
        servicio.side_effect = ValueError("ciudad sin configuración")

        scrape_cartelera_task.apply(args=("cinepolis", "bogota"))

        ejecucion = EjecucionScraping.objects.get()
        self.assertEqual(ejecucion.estado, EjecucionScraping.Estado.FALLIDA)
        self.assertIn("ValueError", ejecucion.mensaje_error)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_si_hay_otra_ejecucion_en_curso_queda_como_omitida(self, servicio):
        with patch("cines.tasks.candado_scraping", _candado_falso(False)):
            scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        servicio.assert_not_called()
        ejecucion = EjecucionScraping.objects.get()
        self.assertEqual(ejecucion.estado, EjecucionScraping.Estado.OMITIDA)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_la_advertencia_de_la_salvaguarda_queda_registrada(self, servicio):
        servicio.return_value = _resultado(
            advertencia="Se omitió la sincronización: la respuesta llegó vacía."
        )

        scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        ejecucion = EjecucionScraping.objects.get()
        self.assertEqual(ejecucion.estado, EjecucionScraping.Estado.EXITOSA)
        self.assertIn("respuesta llegó vacía", ejecucion.advertencia)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_sin_salvaguarda_la_advertencia_queda_vacia(self, servicio):
        servicio.return_value = _resultado()

        scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        self.assertEqual(EjecucionScraping.objects.get().advertencia, "")


class EjecucionScrapingAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_superuser(
            username="root", email="root@example.com", password="x"
        )
        cls.ejecucion = EjecucionScraping.objects.create(
            cine="cinepolis", ciudad="valledupar", funciones_leidas=5
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_el_listado_y_el_detalle_se_pueden_ver(self):
        lista = self.client.get(reverse("admin:cines_ejecucionscraping_changelist"))
        detalle = self.client.get(
            reverse("admin:cines_ejecucionscraping_change", args=[self.ejecucion.pk])
        )

        self.assertEqual(lista.status_code, 200)
        self.assertEqual(detalle.status_code, 200)

    def test_es_de_solo_lectura(self):
        agregar = self.client.get(reverse("admin:cines_ejecucionscraping_add"))
        self.assertEqual(agregar.status_code, 403)

        url = reverse("admin:cines_ejecucionscraping_change", args=[self.ejecucion.pk])
        self.client.post(url, {"cine": "otro", "ciudad": "x", "estado": "fallida"})
        self.ejecucion.refresh_from_db()
        self.assertEqual(self.ejecucion.cine, "cinepolis")

        borrar = self.client.post(
            reverse("admin:cines_ejecucionscraping_delete", args=[self.ejecucion.pk]),
            {"post": "yes"},
        )
        self.assertEqual(borrar.status_code, 403)
        self.assertTrue(EjecucionScraping.objects.exists())