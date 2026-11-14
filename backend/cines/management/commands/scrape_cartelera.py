from django.core.management.base import BaseCommand, CommandError
from cines.services import (
    CITY_PROVIDER_KEYS,
    SCRAPERS,
    ScraperError,
    scrape_and_save_cartelera,
)

class Command(BaseCommand):
    help = "Obtiene la cartelera de un cine, relaciona películas y guarda funciones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cine",
            required=True,
            choices=tuple(SCRAPERS),
            help="Cine cuyo scraper se ejecutará.",
        )
        parser.add_argument(
            "--ciudad",
            default="bogota",
            choices=tuple(CITY_PROVIDER_KEYS),
            help="Ciudad canónica (por defecto: bogota).",
        )

    def handle(self, *_args, **options):
        try:
            result = scrape_and_save_cartelera(
                cinema_provider=options["cine"],
                city_slug=options["ciudad"],
            )
        except (ScraperError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Cartelera {result.cine} ({result.ciudad}): "
                f"{result.funciones_leidas} funciones leídas, "
                f"{result.funciones_asociadas} asociadas al catálogo, "
                f"{result.funciones_creadas} guardadas, "
                f"{result.funciones_actualizadas} actualizadas, "
                f"{result.titulos_pendientes} pendientes de revisión, "
                f"{result.peliculas_en_cartelera} películas pasadas a 'en cartelera', "
                f"{result.estrenos_leidos} próximos estrenos leídos, "
                f"{result.estrenos_asociados} asociados a Media, "
                f"{result.funciones_vencidas_eliminadas} funciones vencidas eliminadas, "
                f"{result.funciones_obsoletas_eliminadas} funciones futuras obsoletas "
                "eliminadas, "
                f"{result.peliculas_fuera_cartelera} películas pasadas a "
                "'fuera de cartelera'."
            )
        )

        if result.estrenos_sin_coincidencia:
            self.stdout.write("Próximos estrenos sin coincidencia en Media:")
            for title in result.estrenos_sin_coincidencia:
                self.stdout.write(f"  {title}")

        if result.titulos_pendientes:
            self.stdout.write("Títulos pendientes:")
            for title in result.titulos_pendientes_mostrar:
                self.stdout.write(f"  {title}")
            if result.titulos_pendientes > len(result.titulos_pendientes_mostrar):
                self.stdout.write("  (se muestran como máximo 20 títulos)")
