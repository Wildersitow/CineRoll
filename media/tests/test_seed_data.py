from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from media.models import Credito, Genero, Media, Persona


class SeedDataCommandTests(TestCase):
    def test_loads_catalog_and_is_idempotent(self):
        call_command("seed_data", stdout=StringIO())

        self.assertGreaterEqual(Media.objects.count(), 30)
        self.assertGreater(Genero.objects.count(), 0)
        self.assertGreater(Persona.objects.count(), 0)
        self.assertGreater(Credito.objects.count(), 0)

        for seeded_media in Media.objects.all():
            self.assertTrue(seeded_media.generos.exists(), seeded_media.titulo)
            self.assertTrue(
                seeded_media.creditos.filter(rol=Credito.Rol.DIRECTOR).exists(),
                seeded_media.titulo,
            )
            self.assertTrue(
                seeded_media.creditos.filter(rol=Credito.Rol.ACTOR).exists(),
                seeded_media.titulo,
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