"""Creación automática de películas cuando el scraper trae un título sin ficha."""

from datetime import date, timedelta
from io import StringIO
from unittest import TestCase as SimpleTestCase
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from cines import tmdb
from cines.metadata import extract_movie_metadata, parse_duration
from cines.models import Funcion, TituloPendiente
from cines.scrapers.cinepolis import parse_cartelera_data as parse_cinepolis
from cines.scrapers.royal_films import parse_cartelera_data as parse_royal
from cines.services import (
    CarteleraData,
    normalize_title,
    pretty_title,
    scrape_and_save_cartelera,
)
from media.models import Credito, Media


def _funcion(titulo, cine="Cinépolis Mega Mall", dias=1, hora=20, **extra):
    momento = timezone.localtime(timezone.now() + timedelta(days=dias)).replace(
        hour=hora, minute=0, second=0, microsecond=0
    )
    return {
        "titulo": titulo,
        "cine": cine,
        "ciudad": "valledupar",
        "fecha": momento.date(),
        "hora": momento.timetz(),
        "sala": "Sala 1",
        "formato": "2D, Doblada",
        "fuente_scraping": "https://cinepolis.com.co/",
        "cine_id_origen": "577",
        "funcion_id_origen": f"{titulo}-{dias}-{hora}",
        **extra,
    }


AVENGERS_META = {
    "sinopsis": "Los Vengadores se reúnen otra vez para enfrentar al Doctor Doom.",
    "duracion": 150,
    "poster_url": "https://static.cinepolis.com/img/peliculas/1/avengers.jpg",
    "generos": ["Acción", "Aventura"],
}


@patch("cines.scrapers.cinepolis.scrape_cartelera_completa")
class CreacionAutomaticaTests(TestCase):
    def _scrape(self, scrape, funciones, peliculas=None, proximos=None, **kwargs):
        scrape.return_value = CarteleraData(
            funciones=funciones,
            proximos_estrenos=proximos or [],
            peliculas=peliculas or {},
        )
        return scrape_and_save_cartelera("cinepolis", "valledupar", **kwargs)

    def test_crea_la_pelicula_con_los_datos_del_cine_y_guarda_sus_funciones(self, scrape):
        result = self._scrape(
            scrape,
            [_funcion("Avengers: Doomsday"), _funcion("Avengers: Doomsday", hora=22)],
            peliculas={"avengers doomsday": AVENGERS_META},
        )

        media = Media.objects.get()
        self.assertEqual(media.titulo, "Avengers: Doomsday")
        self.assertEqual(media.tipo, Media.Tipo.PELICULA)
        self.assertTrue(media.creado_automaticamente)
        self.assertEqual(media.sinopsis, AVENGERS_META["sinopsis"])
        self.assertEqual(media.duracion, 150)
        self.assertEqual(media.poster_url, AVENGERS_META["poster_url"])
        self.assertEqual(
            sorted(media.generos.values_list("nombre", flat=True)),
            ["Acción", "Aventura"],
        )
        self.assertEqual(media.estado, Media.Estado.EN_CARTELERA)
        self.assertEqual(Funcion.objects.filter(media=media).count(), 2)
        self.assertEqual(result.funciones_asociadas, 2)
        self.assertEqual(result.titulos_pendientes, 0)
        self.assertEqual(result.peliculas_creadas, 1)
        self.assertEqual(TituloPendiente.objects.count(), 0)

    def test_variantes_de_mayusculas_y_formato_no_duplican_la_pelicula(self, scrape):
        self._scrape(
            scrape,
            [
                _funcion("AVENGERS: DOOMSDAY (DOB 2D)"),
                _funcion("Avengers: Doomsday", cine="Royal Films Guatapurí", hora=18),
                _funcion("PREVENTA - AVENGERS: DOOMSDAY SUB", cine="CineLand", hora=21),
            ],
        )

        media = Media.objects.get()
        # Se prefiere la variante escrita con mayúsculas y minúsculas.
        self.assertEqual(media.titulo, "Avengers: Doomsday")
        self.assertEqual(Funcion.objects.filter(media=media).count(), 3)

    def test_una_segunda_corrida_reutiliza_la_pelicula_creada(self, scrape):
        self._scrape(scrape, [_funcion("COYOTE VS. ACME")])
        self._scrape(scrape, [_funcion("Coyote vs. Acme", hora=15)])

        media = Media.objects.get()
        self.assertEqual(media.titulo, "Coyote vs. Acme")
        self.assertEqual(Funcion.objects.filter(media=media).count(), 1)

    def test_titulo_sin_subtitulo_se_asocia_a_la_pelicula_vigente(self, scrape):
        self._scrape(scrape, [_funcion("HECHIZO: BIENVENIDOS A HEXE")])
        result = self._scrape(scrape, [_funcion("HECHIZO", cine="Royal Films", hora=17)])

        media = Media.objects.get()
        self.assertEqual(media.titulo, "Hechizo: Bienvenidos a Hexe")
        self.assertEqual(result.peliculas_creadas, 0)
        self.assertEqual(Funcion.objects.get().media, media)
        alias = TituloPendiente.objects.get(titulo_normalizado="hechizo")
        self.assertEqual(alias.estado, TituloPendiente.Estado.RESUELTO)
        self.assertEqual(alias.media_asociada, media)

    def test_subtitulo_no_se_asocia_a_una_pelicula_fuera_de_cartelera(self, scrape):
        vieja = Media.objects.create(
            titulo="Avengers",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.FUERA_CARTELERA,
        )

        self._scrape(scrape, [_funcion("Avengers: Doomsday")])

        self.assertEqual(Media.objects.count(), 2)
        self.assertNotEqual(Funcion.objects.get().media, vieja)

    def test_resuelve_los_pendientes_de_corridas_anteriores(self, scrape):
        self._scrape(
            scrape,
            [_funcion("BTS WORLD TOUR 'ARIRANG' IN JAKARTA: LV")],
            crear_peliculas=False,
        )
        pendiente = TituloPendiente.objects.get()
        self.assertEqual(pendiente.estado, TituloPendiente.Estado.PENDIENTE)
        self.assertEqual(Media.objects.count(), 0)

        self._scrape(scrape, [_funcion("BTS WORLD TOUR 'ARIRANG' IN JAKARTA: LV")])

        media = Media.objects.get()
        self.assertEqual(media.titulo, "BTS World Tour 'Arirang' in Jakarta: LV")
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, TituloPendiente.Estado.RESUELTO)
        self.assertEqual(pendiente.media_asociada, media)
        self.assertEqual(Funcion.objects.get().media, media)

    def test_resuelve_pendientes_de_otros_cines_con_el_mismo_titulo(self, scrape):
        TituloPendiente.objects.create(
            titulo_original="COYOTE VS. ACME",
            titulo_normalizado="coyote vs acme",
            cine_nombre="Royal Films",
            ciudad="valledupar",
        )

        self._scrape(scrape, [_funcion("Coyote vs. Acme")])

        pendiente = TituloPendiente.objects.get()
        self.assertEqual(pendiente.estado, TituloPendiente.Estado.RESUELTO)
        self.assertEqual(pendiente.media_asociada, Media.objects.get())

    def test_titulo_ambiguo_queda_pendiente_sin_crear_otra_ficha(self, scrape):
        Media.objects.create(titulo="Película repetida", tipo=Media.Tipo.PELICULA)
        Media.objects.create(titulo="PELICULA REPETIDA (SUB)", tipo=Media.Tipo.PELICULA)

        result = self._scrape(scrape, [_funcion("Película repetida")])

        self.assertEqual(Media.objects.count(), 2)
        self.assertEqual(result.titulos_pendientes, 1)
        self.assertEqual(result.peliculas_creadas, 0)

    def test_titulo_ignorado_no_crea_pelicula(self, scrape):
        TituloPendiente.objects.create(
            titulo_original="Función privada",
            titulo_normalizado="funcion privada",
            cine_nombre="Cinépolis Mega Mall",
            ciudad="valledupar",
            estado=TituloPendiente.Estado.IGNORADO,
        )

        self._scrape(scrape, [_funcion("FUNCION PRIVADA")])

        self.assertEqual(Media.objects.count(), 0)
        self.assertEqual(Funcion.objects.count(), 0)

    @override_settings(CARTELERA_CREAR_PELICULAS=False)
    def test_el_ajuste_desactiva_la_creacion(self, scrape):
        result = self._scrape(scrape, [_funcion("Coyote vs. Acme")])

        self.assertEqual(Media.objects.count(), 0)
        self.assertEqual(result.titulos_pendientes, 1)

    def test_proximo_estreno_sin_ficha_se_crea_como_proximo_estreno(self, scrape):
        estreno = timezone.localdate() + timedelta(days=30)
        result = self._scrape(
            scrape,
            [],
            proximos=[
                {
                    "titulo": "Zootopia 2",
                    "fecha_estreno": estreno,
                    "fuente_scraping": "https://cinepolis.com.co/",
                }
            ],
        )

        media = Media.objects.get()
        self.assertEqual(media.titulo, "Zootopia 2")
        self.assertEqual(media.estado, Media.Estado.PROXIMO_ESTRENO)
        self.assertEqual(media.fecha_estreno, estreno)
        self.assertEqual(result.estrenos_asociados, 1)

    def test_estreno_posterior_a_la_primera_funcion_se_ajusta(self, scrape):
        lejana = timezone.localdate() + timedelta(days=60)
        self._scrape(
            scrape,
            [_funcion("Coyote vs. Acme")],
            peliculas={"coyote vs acme": {"fecha_estreno": lejana}},
        )

        media = Media.objects.get()
        self.assertEqual(media.fecha_estreno, timezone.localdate() + timedelta(days=1))

    def test_el_comando_muestra_las_peliculas_creadas(self, scrape):
        scrape.return_value = CarteleraData(
            funciones=[_funcion("Coyote vs. Acme")],
            proximos_estrenos=[],
        )
        salida = StringIO()

        call_command("scrape_cartelera", cine="cinepolis", ciudad="valledupar", stdout=salida)

        self.assertIn("1 películas creadas automáticamente", salida.getvalue())
        self.assertIn("Coyote vs. Acme", salida.getvalue())


def _tmdb_falso(path, params):
    if path == "/search/movie":
        return {
            "results": [
                {
                    "id": 99,
                    "title": "Hechizo: Bienvenidos a Hexe",
                    "original_title": "Hexe",
                    "release_date": timezone.localdate().isoformat(),
                },
            ]
        }
    if path == "/movie/99":
        return {
            "id": 99,
            "title": "Hechizo: Bienvenidos a Hexe",
            "original_title": "Hexe",
            "overview": "Una bruja abre las puertas de su pueblo.",
            "runtime": 101,
            "release_date": "2026-01-01",
            "poster_path": "/poster.jpg",
            "backdrop_path": "/fondo.jpg",
            "genres": [{"id": 1, "name": "Fantasía"}],
            "videos": {
                "results": [
                    {"site": "YouTube", "type": "Trailer", "key": "abc123", "official": True}
                ]
            },
            "credits": {
                "cast": [{"name": "Actriz Uno"}, {"name": "Actor Dos"}],
                "crew": [{"name": "Directora", "job": "Director"}],
            },
        }
    raise AssertionError(path)


@override_settings(TMDB_API_KEY="clave-de-prueba")
@patch("cines.scrapers.cinepolis.scrape_cartelera_completa")
class CreacionConTmdbTests(TestCase):
    def _scrape(self, scrape, funciones):
        scrape.return_value = CarteleraData(funciones=funciones, proximos_estrenos=[])
        return scrape_and_save_cartelera("cinepolis", "valledupar")

    @patch("cines.tmdb._get", side_effect=_tmdb_falso)
    def test_completa_la_ficha_con_tmdb(self, _get, scrape):
        self._scrape(scrape, [_funcion("HECHIZO: BIENVENIDOS A HEXE")])

        media = Media.objects.get()
        self.assertEqual(media.tmdb_id, 99)
        self.assertEqual(media.titulo, "Hechizo: Bienvenidos a Hexe")
        self.assertEqual(media.titulo_original, "Hexe")
        self.assertEqual(media.duracion, 101)
        self.assertEqual(media.poster_url, "https://image.tmdb.org/t/p/w500/poster.jpg")
        self.assertEqual(media.backdrop_url, "https://image.tmdb.org/t/p/w1280/fondo.jpg")
        self.assertEqual(media.trailer_url, "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(list(media.generos.values_list("nombre", flat=True)), ["Fantasía"])
        self.assertEqual(
            set(Credito.objects.filter(media=media).values_list("persona__nombre", "rol")),
            {
                ("Actriz Uno", "actor"),
                ("Actor Dos", "actor"),
                ("Directora", "director"),
            },
        )

    @patch("cines.tmdb._get", side_effect=_tmdb_falso)
    def test_otro_titulo_con_el_mismo_id_de_tmdb_reutiliza_la_ficha(self, _get, scrape):
        self._scrape(scrape, [_funcion("HECHIZO: BIENVENIDOS A HEXE")])
        # TMDB reconoce el título original "Hexe" como la misma película.
        with patch(
            "cines.tmdb.buscar_pelicula",
            return_value=tmdb.obtener_detalle(99),
        ):
            self._scrape(scrape, [_funcion("HEXE (SUB)", hora=16)])

        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(Funcion.objects.get().media.tmdb_id, 99)

    @patch("cines.tmdb._get", side_effect=_tmdb_falso)
    def test_asigna_tmdb_a_la_ficha_existente_con_el_titulo_de_tmdb(self, _get, scrape):
        existente = Media.objects.create(
            titulo="Hechizo: Bienvenidos a Hexe",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.FUERA_CARTELERA,
        )

        # TMDB encuentra "Hexe" por su título original y devuelve el título en español.
        self._scrape(scrape, [_funcion("HEXE (DOB)")])

        existente.refresh_from_db()
        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(existente.tmdb_id, 99)
        self.assertEqual(Funcion.objects.get().media, existente)

    @patch("cines.tmdb._get", side_effect=tmdb.TmdbError("sin red"))
    def test_si_tmdb_falla_se_crea_con_los_datos_del_cine(self, _get, scrape):
        self._scrape(scrape, [_funcion("Coyote vs. Acme")])

        media = Media.objects.get()
        self.assertIsNone(media.tmdb_id)
        self.assertEqual(media.titulo, "Coyote vs. Acme")


class TmdbConfiguracionTests(SimpleTestCase):
    def test_en_pruebas_no_usa_la_clave_del_entorno(self):
        with patch("cines.tmdb.config", return_value="clave-real"):
            self.assertFalse(tmdb.configurado())

    def test_elige_la_coincidencia_exacta_mas_reciente(self):
        hoy = timezone.localdate()
        resultados = [
            {"id": 1, "title": "Hechizo", "release_date": "1990-05-01"},
            {"id": 2, "title": "Hechizo", "release_date": hoy.isoformat()},
        ]
        self.assertEqual(tmdb._elegir(resultados, "hechizo", normalize_title)["id"], 2)

    def test_no_elige_resultados_distintos(self):
        resultados = [{"id": 1, "title": "Otra película", "release_date": "2026-01-01"}]
        self.assertIsNone(tmdb._elegir(resultados, "hechizo", normalize_title))


class TitulosTests(SimpleTestCase):
    def test_titulo_bonito(self):
        casos = {
            "AVENGERS: DOOMSDAY": "Avengers: Doomsday",
            "AVENGERS: DOOMSDAY (DOB 2D)": "Avengers: Doomsday",
            "PREVENTA - ZOOTOPIA 2 SUB": "Zootopia 2",
            "HECHIZO: BIENVENIDOS A HEXE": "Hechizo: Bienvenidos a Hexe",
            "BTS WORLD TOUR 'ARIRANG' IN JAKARTA: LV": "BTS World Tour 'Arirang' in Jakarta: LV",
            "ROCKY II": "Rocky II",
            "Coyote vs. ACME": "Coyote vs. ACME",
            "COYOTE VS. ACME": "Coyote vs. Acme",
        }
        for crudo, esperado in casos.items():
            with self.subTest(crudo=crudo):
                self.assertEqual(pretty_title(crudo), esperado)

    def test_preventa_y_formatos_no_cambian_la_clave(self):
        self.assertEqual(
            normalize_title("PREVENTA - AVENGERS: DOOMSDAY 4DX SUB"),
            normalize_title("Avengers: Doomsday"),
        )
        self.assertEqual(normalize_title("Preventa"), "preventa")


class MetadatosTests(SimpleTestCase):
    def test_lee_campos_con_nombres_distintos(self):
        metadata = extract_movie_metadata(
            {
                "Title": "Avengers",
                "RatingDescription": "Película para mayores de 12 años en adelante",
                "Synopsis": "<p>Los héroes &amp; villanos se enfrentan.</p> Otra vez.",
                "RunTime": "150 min",
                "Poster": "//static.cinepolis.com/img/peliculas/avengers.jpg",
                "Trailer": "https://www.youtube.com/watch?v=xyz",
                "GenreId": 4,
                "Genre": "ACCIÓN, AVENTURA",
                "OpeningDate": "2026-12-18T00:00:00",
            }
        )
        self.assertEqual(
            metadata,
            {
                "sinopsis": "Los héroes & villanos se enfrentan. Otra vez.",
                "duracion": 150,
                "poster_url": "https://static.cinepolis.com/img/peliculas/avengers.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=xyz",
                "fecha_estreno": date(2026, 12, 18),
                "generos": ["Acción", "Aventura"],
            },
        )

    def test_ruta_relativa_del_poster_usa_la_url_del_cine(self):
        metadata = extract_movie_metadata(
            {"pelicula_imagen": "uploads/peliculas/hexe.jpg"},
            "https://cinemasroyalfilms.com/",
        )
        self.assertEqual(
            metadata["poster_url"],
            "https://cinemasroyalfilms.com/uploads/peliculas/hexe.jpg",
        )

    def test_duraciones(self):
        for valor, esperado in (
            ("1h 58min", 118),
            ("01:58", 118),
            ("118", 118),
            (7080, 118),
            ("2 horas", 120),
            ("sin dato", None),
            (5, None),
        ):
            with self.subTest(valor=valor):
                self.assertEqual(parse_duration(valor), esperado)


class MetadatosEnScrapersTests(SimpleTestCase):
    def test_cinepolis_expone_los_datos_de_cada_pelicula(self):
        payload = {
            "d": {
                "Cinemas": [
                    {
                        "CityKey": "valledupar-colombia",
                        "CityName": "Valledupar, Colombia",
                        "Id": 577,
                        "Name": "Cinépolis Mega Mall",
                        "Dates": [
                            {
                                "FilterDate": "/Date(1794549600000)/",
                                "Movies": [
                                    {
                                        "Title": "AVENGERS: DOOMSDAY",
                                        "OriginalTitle": "Avengers: Doomsday",
                                        "RunTime": "150 min",
                                        "Poster": "https://static.cinepolis.com/img/avengers.jpg",
                                        "Formats": [
                                            {
                                                "Name": "DOB",
                                                "Language": "DOBLADA",
                                                "Showtimes": [
                                                    {
                                                        "CinemaId": 577,
                                                        "ShowtimeId": "1",
                                                        "Time": "20:10",
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        result = parse_cinepolis(payload, "valledupar-colombia", "https://cinepolis.com.co/")

        self.assertEqual(
            result.peliculas["avengers doomsday"],
            {
                "duracion": 150,
                "poster_url": "https://static.cinepolis.com/img/avengers.jpg",
            },
        )

    def test_royal_films_expone_los_datos_de_cada_pelicula(self):
        billboard = {
            "status": True,
            "data": [
                {
                    "pelicula": {
                        "pelicula_id": 1,
                        "pelicula_titulo": "COYOTE VS. ACME",
                        "pelicula_sinopsis": "Wile E. Coyote demanda a la empresa ACME.",
                        "pelicula_duracion": 95,
                        "pelicula_imagen": "https://cinemasroyalfilms.com/img/coyote.jpg",
                    }
                }
            ],
        }
        funciones = {"1": {"status": True, "data": []}}

        result = parse_royal(billboard, funciones, "1006")

        self.assertEqual(
            result.peliculas["coyote vs acme"],
            {
                "sinopsis": "Wile E. Coyote demanda a la empresa ACME.",
                "duracion": 95,
                "poster_url": "https://cinemasroyalfilms.com/img/coyote.jpg",
            },
        )


@override_settings(TMDB_API_KEY="clave-de-prueba")
class CompletarConTmdbTests(TestCase):
    @patch("cines.tmdb._get", side_effect=_tmdb_falso)
    def test_completa_solo_los_campos_vacios(self, _get):
        media = Media.objects.create(
            titulo="Hechizo: Bienvenidos a Hexe",
            tipo=Media.Tipo.PELICULA,
            sinopsis="Sinopsis del cine.",
            creado_automaticamente=True,
        )
        salida = StringIO()

        call_command("completar_peliculas_tmdb", stdout=salida)

        media.refresh_from_db()
        self.assertEqual(media.tmdb_id, 99)
        self.assertEqual(media.sinopsis, "Sinopsis del cine.")
        self.assertEqual(media.duracion, 101)
        self.assertEqual(media.poster_url, "https://image.tmdb.org/t/p/w500/poster.jpg")
        self.assertTrue(media.creditos.exists())
        self.assertIn("1 películas completadas", salida.getvalue())

    def test_sin_clave_avisa(self):
        with override_settings(TMDB_API_KEY=""):
            with self.assertRaises(Exception):
                call_command("completar_peliculas_tmdb")
