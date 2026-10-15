from django.contrib import admin

from media.models import Credito, Genero, Media, Persona


class CreditoInline(admin.TabularInline):
	model = Credito
	extra = 1
	autocomplete_fields = ("persona",)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
	list_display = ("titulo", "titulo_original", "tipo", "estado", "fecha_estreno")
	list_filter = ("tipo", "estado", "generos")
	search_fields = ("titulo", "titulo_original", "sinopsis")
	filter_horizontal = ("generos",)
	inlines = (CreditoInline,)


@admin.register(Genero)
class GeneroAdmin(admin.ModelAdmin):
	list_display = ("nombre",)
	search_fields = ("nombre",)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
	list_display = ("nombre", "fecha_nacimiento")
	search_fields = ("nombre", "biografia")
	list_filter = ("fecha_nacimiento",)


@admin.register(Credito)
class CreditoAdmin(admin.ModelAdmin):
	list_display = ("media", "persona", "rol")
	list_filter = ("rol",)
	search_fields = ("media__titulo", "persona__nombre")
	autocomplete_fields = ("media", "persona")
	list_select_related = ("media", "persona")
