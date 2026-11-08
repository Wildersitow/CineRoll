"""Permisos reutilizables para todo el proyecto.

Roles: visitante (sin sesión), usuario registrado y administrador (is_staff).
Cualquier app los importa así:  from usuarios.permissions import EsAutorOLecturaPublica
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


def _autenticado(request):
    return bool(request.user and request.user.is_authenticated)


class EsAdministrador(BasePermission):
    """Solo administradores (is_staff), tanto para leer como para escribir."""

    def has_permission(self, request, view):
        return _autenticado(request) and request.user.is_staff


class EsAdministradorOLecturaPublica(BasePermission):
    """Lectura abierta para visitantes; escritura solo para administradores."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (
            _autenticado(request) and request.user.is_staff
        )


class EsAutorOLecturaPublica(BasePermission):
    """Lectura abierta; escribir exige sesión y, sobre un objeto, ser su autor.

    El modelo debe tener una FK al usuario llamada `usuario`. Si se llama distinto,
    la vista define `campo_autor = "nombre_del_campo"`.
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or _autenticado(request)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        campo = getattr(view, "campo_autor", "usuario")
        return getattr(obj, f"{campo}_id", None) == request.user.pk
