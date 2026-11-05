from django.contrib import admin

from social.models import Resena


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ("media", "usuario", "puntuacion", "oculta", "fecha_creacion")
    list_filter = ("oculta", "puntuacion", "fecha_creacion")
    search_fields = ("media__titulo", "usuario__username", "texto")
    autocomplete_fields = ("usuario", "media")
    list_select_related = ("usuario", "media")
    date_hierarchy = "fecha_creacion"
    actions = ("ocultar_resenas", "mostrar_resenas")

    @admin.action(description="Ocultar reseñas seleccionadas")
    def ocultar_resenas(self, request, queryset):
        cantidad = queryset.update(oculta=True)
        self.message_user(request, f"{cantidad} reseña(s) ocultada(s).")

    @admin.action(description="Volver a mostrar reseñas seleccionadas")
    def mostrar_resenas(self, request, queryset):
        cantidad = queryset.update(oculta=False)
        self.message_user(request, f"{cantidad} reseña(s) visible(s) de nuevo.")
