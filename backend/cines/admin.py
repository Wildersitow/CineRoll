from django.contrib import admin

from cines.models import Cine, Funcion, TituloPendiente


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
    actions = ("marcar_ignorados", "volver_a_pendientes")

    def save_model(self, request, obj, form, change):
        # Elegir una película es resolver el título; quitarla lo devuelve a pendiente.
        if obj.media_asociada_id and obj.estado == TituloPendiente.Estado.PENDIENTE:
            obj.estado = TituloPendiente.Estado.RESUELTO
        elif not obj.media_asociada_id and obj.estado == TituloPendiente.Estado.RESUELTO:
            obj.estado = TituloPendiente.Estado.PENDIENTE
        super().save_model(request, obj, form, change)

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