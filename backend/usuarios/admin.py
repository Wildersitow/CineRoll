from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Perfil", {"fields": ("avatar", "biografia", "escala_calificacion")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Perfil", {"fields": ("email", "avatar", "biografia", "escala_calificacion")}),
    )