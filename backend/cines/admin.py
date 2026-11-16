from django.contrib import admin
from django.db import transaction

from cines.models import Cine, Funcion, TituloPendiente
from media.models import Media


@admin.register(Cine)
class CineAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ciudad", "direccion", "sitio_web")
    list_filter = ("ciudad",)
    search_fields = ("nombre", "ciudad", "direccion")


@admin.register(Funcion)
class FuncionAdmin(admin.ModelAdmin):
    list_display = ("media", "cine", "fecha_hora", "sala", "formato", "fecha_actualizacion")
    list_filter = ("cine", "formato", "fecha_hora")
    search_fields = ("media__titulo", "cine__nombre", "sala")
    autocomplete_fields = ("media", "cine")
    list_select_related = ("media", "cine")
    date_hierarchy = "fecha_hora"
    readonly_fields = ("fecha_actualizacion",)


@admin.register(TituloPendiente)
class TituloPendienteAdmin(admin.ModelAdmin):
    """Revisión manual de los títulos que el scraper no pudo asociar al catálogo.

    Para resolver uno: abrirlo, elegir la película en "Media asociada" y guardar.
    En la siguiente ejecución del scraper sus funciones se guardan con esa película.
    """

    list_display = (
        "titulo_original",
        "cine_nombre",
        "ciudad",
        "estado",
        "media_asociada",
        "apariciones_detectadas",
        "ultima_deteccion",
    )
    list_filter = ("estado", "ciudad", "cine_nombre")
    search_fields = ("titulo_original", "titulo_normalizado", "cine_nombre")
    autocomplete_fields = ("media_asociada",)
    list_select_related = ("media_asociada",)
    readonly_fields = (
        "titulo_original",
        "titulo_normalizado",
        "cine_nombre",
        "ciudad",
        "fuente_scraping",
        "primera_deteccion",
        "ultima_deteccion",
        "apariciones_detectadas",
    )
    actions = (
        "crear_fichas_borrador",
        "marcar_ignorados",
        "volver_a_pendientes",
    )

    def save_model(self, request, obj, form, change):
        # Elegir una película es resolver el título; quitarla lo devuelve a pendiente.
        if obj.media_asociada_id and obj.estado == TituloPendiente.Estado.PENDIENTE:
            obj.estado = TituloPendiente.Estado.RESUELTO
        elif not obj.media_asociada_id and obj.estado == TituloPendiente.Estado.RESUELTO:
            obj.estado = TituloPendiente.Estado.PENDIENTE
        super().save_model(request, obj, form, change)

    @admin.action(description="Crear ficha borrador en el catálogo")
    def crear_fichas_borrador(self, request, queryset):
        fichas_por_titulo = {}
        pendientes_resueltos = 0

        with transaction.atomic():
            for pendiente in queryset:
                if (
                    pendiente.estado != TituloPendiente.Estado.PENDIENTE
                    or pendiente.media_asociada_id
                    or not pendiente.titulo_normalizado
                ):
                    continue

                media = fichas_por_titulo.get(pendiente.titulo_normalizado)
                if media is None:
                    media = Media.objects.create(
                        titulo=pendiente.titulo_normalizado,
                        tipo=Media.Tipo.PELICULA,
                        estado=Media.Estado.EN_CARTELERA,
                    )
                    fichas_por_titulo[pendiente.titulo_normalizado] = media

                pendiente.media_asociada = media
                pendiente.estado = TituloPendiente.Estado.RESUELTO
                pendiente.save(update_fields=("media_asociada", "estado"))
                pendientes_resueltos += 1

        self.message_user(
            request,
            f"{len(fichas_por_titulo)} ficha(s) borrador creada(s) y "
            f"{pendientes_resueltos} título(s) pendiente(s) resuelto(s).",
        )

    @admin.action(description="Marcar como ignorados (no son películas del catálogo)")
    def marcar_ignorados(self, request, queryset):
        cantidad = queryset.update(
            estado=TituloPendiente.Estado.IGNORADO, media_asociada=None
        )
        self.message_user(request, f"{cantidad} título(s) marcado(s) como ignorado(s).")

    @admin.action(description="Volver a pendientes de revisión")
    def volver_a_pendientes(self, request, queryset):
        cantidad = queryset.update(
            estado=TituloPendiente.Estado.PENDIENTE, media_asociada=None
        )
        self.message_user(request, f"{cantidad} título(s) de nuevo pendiente(s).")