import json

from django.core.management.base import BaseCommand

from cines.models import TituloPendiente
from media.models import Media


class Command(BaseCommand):
    help = (
        "Lista fichas en cartelera o próximo estreno incompletas y títulos "
        "pendientes sin resolver después de las ejecuciones reales."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Devuelve el informe en formato JSON.",
        )

    def handle(self, *_args, **options):
        fichas = (
            Media.objects.filter(
                estado__in=(
                    Media.Estado.EN_CARTELERA,
                    Media.Estado.PROXIMO_ESTRENO,
                )
            )
            .prefetch_related("generos", "creditos")
            .order_by("estado", "titulo", "pk")
        )

        fichas_incompletas = []
        for ficha in fichas:
            campos = []
            if not ficha.sinopsis.strip():
                campos.append("sinopsis")
            if not ficha.poster_url:
                campos.append("poster")
            if not ficha.trailer_url:
                campos.append("trailer")
            if not ficha.generos.exists():
                campos.append("generos")
            if not ficha.creditos.exists():
                campos.append("reparto")

            if campos:
                fichas_incompletas.append(
                    {
                        "id": ficha.pk,
                        "titulo": ficha.titulo,
                        "estado": ficha.estado,
                        "campos_faltantes": campos,
                    }
                )

        pendientes = list(
            TituloPendiente.objects.filter(
                estado=TituloPendiente.Estado.PENDIENTE,
                media_asociada__isnull=True,
            ).order_by("ultima_deteccion", "titulo_normalizado", "pk")
        )
        titulos_pendientes = [
            {
                "id": pendiente.pk,
                "titulo_original": pendiente.titulo_original,
                "cine": pendiente.cine_nombre,
                "ciudad": pendiente.ciudad,
                "apariciones": pendiente.apariciones_detectadas,
                "ultima_deteccion": pendiente.ultima_deteccion.isoformat(),
            }
            for pendiente in pendientes
        ]

        informe = {
            "fichas_incompletas": fichas_incompletas,
            "titulos_pendientes": titulos_pendientes,
        }

        if options["json"]:
            self.stdout.write(json.dumps(informe, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.WARNING("Fichas incompletas:"))
        if fichas_incompletas:
            for ficha in fichas_incompletas:
                faltantes = ", ".join(ficha["campos_faltantes"])
                self.stdout.write(
                    f"  [{ficha['estado']}] #{ficha['id']} {ficha['titulo']} — faltan: {faltantes}"
                )
        else:
            self.stdout.write("  Ninguna.")

        self.stdout.write(self.style.WARNING("Títulos pendientes sin resolver:"))
        if titulos_pendientes:
            for pendiente in titulos_pendientes:
                self.stdout.write(
                    f"  #{pendiente['id']} {pendiente['titulo_original']} — "
                    f"{pendiente['cine']} ({pendiente['ciudad']}), "
                    f"{pendiente['apariciones']} aparición(es)"
                )
        else:
            self.stdout.write("  Ninguno.")
