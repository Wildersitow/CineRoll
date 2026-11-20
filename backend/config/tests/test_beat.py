from django.conf import settings
from django.test import SimpleTestCase

from cines.services import CITY_PROVIDER_KEYS, SCRAPERS
from config.beat import construir_beat_schedule, parsear_pares

PARES = [
    ("cinepolis", "valledupar"),
    ("royal_films", "valledupar"),
    ("cineland", "valledupar"),
]


def _scrapes(schedule):
    return {
        nombre: entrada
        for nombre, entrada in schedule.items()
        if entrada["task"] == "cines.tasks.scrape_cartelera_task"
    }


class ParsearParesTests(SimpleTestCase):
    def test_convierte_texto_en_pares(self):
        self.assertEqual(
            parsear_pares(["cinepolis:valledupar", " Cineland : Valledupar "]),
            [("cinepolis", "valledupar"), ("Cineland", "valledupar")],
        )

    def test_rechaza_formatos_invalidos(self):
        for valor in ("cinepolis", "cinepolis:", ":valledupar", ""):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    parsear_pares([valor])


class ConstruirBeatScheduleTests(SimpleTestCase):
    def test_dos_franjas_con_cines_escalonados(self):
        scrapes = _scrapes(construir_beat_schedule(PARES))

        self.assertEqual(len(scrapes), 6)
        horarios = {
            (entrada["args"][0], next(iter(entrada["schedule"].hour)),
             next(iter(entrada["schedule"].minute)))
            for entrada in scrapes.values()
        }
        self.assertEqual(
            horarios,
            {
                ("cinepolis", 6, 0), ("royal_films", 6, 10), ("cineland", 6, 20),
                ("cinepolis", 18, 0), ("royal_films", 18, 10), ("cineland", 18, 20),
            },
        )

    def test_cada_tarea_recibe_cine_y_ciudad(self):
        scrapes = _scrapes(construir_beat_schedule(PARES))

        self.assertEqual(
            {entrada["args"] for entrada in scrapes.values()}, set(PARES)
        )

    def test_el_espaciado_puede_pasar_de_la_hora(self):
        scrapes = _scrapes(
            construir_beat_schedule(PARES, horas=(6,), espaciado_minutos=30)
        )

        horarios = sorted(
            (next(iter(e["schedule"].hour)), next(iter(e["schedule"].minute)))
            for e in scrapes.values()
        )
        self.assertEqual(horarios, [(6, 0), (6, 30), (7, 0)])

    def test_nunca_mas_de_dos_ejecuciones_diarias_por_cine(self):
        with self.assertRaises(ValueError):
            construir_beat_schedule(PARES, horas=(6, 12, 18))
        with self.assertRaises(ValueError):
            construir_beat_schedule(PARES, horas=(6, 6))
        with self.assertRaises(ValueError):
            construir_beat_schedule(PARES, horas=())

    def test_incluye_la_limpieza_de_funciones_vencidas(self):
        schedule = construir_beat_schedule(PARES)

        self.assertEqual(
            schedule["limpiar-cartelera-vencida"]["task"],
            "cines.tasks.limpiar_cartelera_vencida",
        )

    def test_sin_cines_solo_quedan_las_limpiezas(self):
        schedule = construir_beat_schedule([])

        self.assertEqual(
        set(schedule),
        {"limpiar-cartelera-vencida", "limpiar-tokens-vencidos"},
        )

    def test_incluye_la_limpieza_semanal_de_tokens(self):
        entrada = construir_beat_schedule(PARES)["limpiar-tokens-vencidos"]

        self.assertEqual(entrada["task"], "usuarios.tasks.limpiar_tokens_vencidos")
        self.assertEqual(entrada["schedule"].day_of_week, {0})  # domingo
        self.assertEqual(entrada["schedule"].hour, {3})
        self.assertEqual(entrada["schedule"].minute, {0})


class ConfiguracionActivaTests(SimpleTestCase):
    def test_los_pares_configurados_existen_en_el_registro_de_scrapers(self):
        for cine, ciudad in settings.CARTELERA_ACTIVA:
            with self.subTest(cine=cine, ciudad=ciudad):
                self.assertIn(cine, SCRAPERS)
                self.assertIn(cine, CITY_PROVIDER_KEYS.get(ciudad, {}))

    def test_el_horario_de_settings_usa_la_zona_de_bogota(self):
        self.assertEqual(settings.CELERY_TIMEZONE, "America/Bogota")
        self.assertEqual(
            len(_scrapes(settings.CELERY_BEAT_SCHEDULE)),
            len(settings.CARTELERA_ACTIVA) * 2,
        )