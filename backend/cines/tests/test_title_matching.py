from unittest import TestCase

from django.test import TestCase as DjangoTestCase

from cines.services import match_media_title, normalize_title
from media.models import Media


class TitleNormalizationTests(TestCase):
    def test_removes_accents_case_and_showing_qualifiers(self):
        self.assertEqual(
            normalize_title("  PELÍCULA: La Acción (DOB 2D)  "),
            "pelicula la accion",
        )

    def test_preserves_words_that_are_part_of_a_title(self):
        self.assertEqual(normalize_title("El original"), "el original")


class MediaTitleMatchingTests(DjangoTestCase):
    def test_matches_accented_catalog_title_and_strips_showtime_suffix(self):
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            titulo_original="How to Train Your Dragon",
            tipo=Media.Tipo.PELICULA,
        )

        result = match_media_title("COMO ENTRENAR A TU DRAGON (DOB 2D)")

        self.assertEqual(result, media)

    def test_matches_original_title(self):
        media = Media.objects.create(
            titulo="El caballero oscuro",
            titulo_original="The Dark Knight",
            tipo=Media.Tipo.PELICULA,
        )

        self.assertEqual(match_media_title("THE DARK KNIGHT (SUB 3D)"), media)

    def test_does_not_match_series_or_unknown_titles(self):
        Media.objects.create(
            titulo="Título que sí existe",
            tipo=Media.Tipo.SERIE,
        )

        self.assertIsNone(match_media_title("Título que sí existe"))
        self.assertIsNone(match_media_title("Película desconocida"))

    def test_ambiguous_catalog_match_is_not_assigned(self):
        Media.objects.create(titulo="Película repetida", tipo=Media.Tipo.PELICULA)
        Media.objects.create(titulo="PELICULA REPETIDA (DOB 2D)", tipo=Media.Tipo.PELICULA)

        self.assertIsNone(match_media_title("Película repetida"))
