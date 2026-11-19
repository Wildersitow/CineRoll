from django import forms
from django.contrib import admin
from django.template.response import TemplateResponse

from social.models import (
    ElementoLista,
    Lista,
    ReporteResena,
    Resena,
    Seguimiento,
    SugerenciaEdicion,
)
from social.sugerencias import aprobar_sugerencia, rechazar_sugerencia


class ElementoListaInline(admin.TabularInline):
    model = ElementoLista
    extra = 1
    autocomplete_fields = ("media",)


@admin.register(Lista)
class ListaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "usuario",
        "tipo",
        "publica",
        "total_elementos",
        "fecha_creacion",
    )
    list_filter = ("tipo", "publica", "fecha_creacion")
    search_fields = ("nombre", "usuario__username", "descripcion")
    autocomplete_fields = ("usuario",)
    list_select_related = ("usuario",)
    date_hierarchy = "fecha_creacion"
    inlines = [ElementoListaInline]

    @admin.display(description="Total elementos")
    def total_elementos(self, obj):
        return obj.total_elementos


@admin.register(ElementoLista)
class ElementoListaAdmin(admin.ModelAdmin):
    list_display = ("lista", "media", "orden", "fecha_agregado")
    list_filter = ("fecha_agregado",)
    search_fields = ("lista__nombre", "media__titulo", "lista__usuario__username")
    autocomplete_fields = ("lista", "media")
    list_select_related = ("lista", "media", "lista__usuario")


@admin.register(Seguimiento)
class SeguimientoAdmin(admin.ModelAdmin):
    list_display = ("seguidor", "seguido", "fecha_creacion")
    list_filter = ("fecha_creacion",)
    search_fields = ("seguidor__username", "seguido__username")
    autocomplete_fields = ("seguidor", "seguido")
    list_select_related = ("seguidor", "seguido")
    date_hierarchy = "fecha_creacion"


@admin.register(SugerenciaEdicion)
class SugerenciaEdicionAdmin(admin.ModelAdmin):
    list_display = (
        "media",
        "usuario",
        "campo",
        "valor_actual",
        "valor_propuesto",
        "estado",
        "revisado_por",
        "fecha_creacion",
        "fecha_resolucion",
    )
    list_filter = ("estado", "campo", "fecha_creacion")
    search_fields = (
        "media__titulo",
        "usuario__username",
        "valor_propuesto",
        "valor_anterior",
        "motivo",
    )
    readonly_fields = (
        "estado",
        "revisado_por",
        "fecha_resolucion",
        "motivo_rechazo",
        "valor_anterior",
        "valor_actual",
        "fecha_creacion",
    )
    autocomplete_fields = ("usuario", "media")
    list_select_related = ("usuario", "media", "revisado_por")
    date_hierarchy = "fecha_creacion"
    actions = ("aprobar_sugerencias", "rechazar_sugerencias")

    @admin.display(description="Valor actual")
    def valor_actual(self, obj):
        if obj.pk and obj.media_id:
            if obj.estado == SugerenciaEdicion.Estado.APROBADA:
                return obj.valor_anterior
            valor = getattr(obj.media, obj.campo, None)
            if hasattr(valor, "isoformat"):
                return valor.isoformat()
            return "" if valor is None else str(valor)
        return "—"

    @admin.action(description="Aprobar sugerencias seleccionadas")
    def aprobar_sugerencias(self, request, queryset):
        aprobadas = 0
        errores = 0
        for sugerencia in queryset:
            try:
                aprobar_sugerencia(sugerencia, request.user)
                aprobadas += 1
            except Exception:
                errores += 1
        if aprobadas:
            self.message_user(request, f"{aprobadas} sugerencia(s) aprobada(s).")
        if errores:
            self.message_user(request, f"{errores} sugerencia(s) no pudieron aprobarse.")

    @admin.action(description="Rechazar sugerencias seleccionadas")
    def rechazar_sugerencias(self, request, queryset):
        seleccionadas = list(queryset.values_list("pk", flat=True))
        if not seleccionadas:
            self.message_user(request, "No se seleccionaron sugerencias.")
            return None

        if request.POST.get("confirmar_rechazo"):
            form = MotivoRechazoMasivoForm(request.POST)
            if form.is_valid():
                motivo = form.cleaned_data["motivo_rechazo"]
                rechazadas = 0
                errores = 0
                for sugerencia in queryset:
                    try:
                        rechazar_sugerencia(
                            sugerencia,
                            request.user,
                            motivo_rechazo=motivo,
                        )
                        rechazadas += 1
                    except Exception:
                        errores += 1
                if rechazadas:
                    self.message_user(request, f"{rechazadas} sugerencia(s) rechazada(s).")
                if errores:
                    self.message_user(request, f"{errores} sugerencia(s) no pudieron rechazarse.")
                return None
        else:
            form = MotivoRechazoMasivoForm(initial={"_selected_action": seleccionadas})

        return TemplateResponse(
            request,
            "admin/social/sugerencia_rechazo_confirmacion.html",
            {
                "title": "Rechazar sugerencias seleccionadas",
                "sugerencias": queryset,
                "form": form,
                "action_name": "rechazar_sugerencias",
                "opts": self.model._meta,
            },
        )


class MotivoRechazoMasivoForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    motivo_rechazo = forms.CharField(
        label="Motivo del rechazo",
        widget=forms.Textarea(attrs={"rows": 4}),
    )


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


@admin.register(ReporteResena)
class ReporteResenaAdmin(admin.ModelAdmin):
    list_display = ("resena", "usuario", "motivo", "fecha")
    list_filter = ("fecha",)
    search_fields = (
        "resena__media__titulo",
        "resena__usuario__username",
        "usuario__username",
        "motivo",
    )
    raw_id_fields = ("resena", "usuario")
    list_select_related = ("resena", "resena__media", "resena__usuario", "usuario")
    date_hierarchy = "fecha"
    actions = ("ocultar_resenas_reportadas",)

    @admin.action(description="Ocultar reseñas de los reportes seleccionados")
    def ocultar_resenas_reportadas(self, request, queryset):
        cantidad = Resena.objects.filter(
            pk__in=queryset.values("resena_id"), oculta=False
        ).update(oculta=True)
        self.message_user(request, f"{cantidad} reseña(s) reportada(s) ocultada(s).")
