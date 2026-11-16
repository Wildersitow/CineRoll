from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from cines.services import match_media_title
from media.models import Credito, Genero, Media, Persona


class SeedDataCommandTests(TestCase):
    def test_seeds_movies_currently_screening_in_valledupar(self):
        call_command("seed_data", stdout=StringIO())

        current_titles = {
            "Cómo robar un banco",
            "Ebenezer",
            "El gato con sombrero",
            "Godzilla Minus Zero",
            "RE: Encanto",
            "Yo soy Rocky",
            "Clayface",
            "Wildwood: El Bosque Salvaje",
            "El corazón de la bestia",
            "Verity",
        }
        current_media = Media.objects.filter(titulo__in=current_titles)

        self.assertSetEqual(
            set(current_media.values_list("titulo", flat=True)), current_titles
        )
        self.assertFalse(
            current_media.exclude(estado=Media.Estado.EN_CARTELERA).exists()
        )
        encanto = Media.objects.get(titulo="RE: Encanto")
        self.assertEqual(match_media_title("Encanto"), encanto)
        self.assertEqual(match_media_title("RE: Encanto"), encanto)

    def test_loads_catalog_and_is_idempotent(self):
        call_command("seed_data", stdout=StringIO())

        self.assertGreaterEqual(Media.objects.count(), 30)
        self.assertGreater(Genero.objects.count(), 0)
        self.assertGreater(Persona.objects.count(), 0)
        self.assertGreater(Credito.objects.count(), 0)

        for seeded_media in Media.objects.all():
            self.assertTrue(seeded_media.sinopsis, seeded_media.titulo)
            self.assertTrue(seeded_media.poster_url, seeded_media.titulo)
            self.assertTrue(seeded_media.trailer_url, seeded_media.titulo)
            self.assertTrue(seeded_media.generos.exists(), seeded_media.titulo)
            self.assertTrue(
                seeded_media.creditos.filter(rol=Credito.Rol.DIRECTOR).exists(),
                seeded_media.titulo,
            )
            self.assertTrue(
                seeded_media.creditos.filter(rol=Credito.Rol.ACTOR).exists(),
                seeded_media.titulo,
            )

        upcoming = Media.objects.filter(estado=Media.Estado.PROXIMO_ESTRENO)
        self.assertGreaterEqual(upcoming.count(), 5)
        self.assertGreaterEqual(
            upcoming.filter(fecha_estreno__gt=timezone.localdate()).count(), 5
        )

        media = Media.objects.get(titulo="Cadena perpetua")
        self.assertGreater(media.generos.count(), 0)
        self.assertTrue(
            media.creditos.filter(rol=Credito.Rol.DIRECTOR).exists()
        )
        self.assertTrue(media.creditos.filter(rol=Credito.Rol.ACTOR).exists())

        counts_after_first_run = (
            Media.objects.count(),
            Genero.objects.count(),
            Persona.objects.count(),
            Credito.objects.count(),
        )

        output = StringIO()
        call_command("seed_data", stdout=output)

        counts_after_second_run = (
            Media.objects.count(),
            Genero.objects.count(),
            Persona.objects.count(),
            Credito.objects.count(),
        )
        self.assertEqual(counts_after_first_run, counts_after_second_run)
        self.assertIn("0 nuevas", output.getvalue())

    def test_no_pisa_estado_ni_fecha_de_titulos_existentes(self):
        call_command("seed_data", stdout=StringIO())
        en_cartelera = Media.objects.get(titulo="Cadena perpetua")
        en_cartelera.estado = Media.Estado.EN_CARTELERA
        en_cartelera.fecha_estreno = date(2026, 12, 1)
        en_cartelera.save()
        proximo = Media.objects.get(titulo="Jumanji 3")
        proximo.fecha_estreno = date(2027, 1, 15)
        proximo.save()

        call_command("seed_data", stdout=StringIO())

        en_cartelera.refresh_from_db()
        proximo.refresh_from_db()
        self.assertEqual(en_cartelera.estado, Media.Estado.EN_CARTELERA)
        self.assertEqual(en_cartelera.fecha_estreno, date(2026, 12, 1))
        self.assertEqual(proximo.estado, Media.Estado.PROXIMO_ESTRENO)
        self.assertEqual(proximo.fecha_estreno, date(2027, 1, 15))