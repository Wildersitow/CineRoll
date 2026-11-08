"""Formato único de errores para toda la API.

Todas las respuestas de error tienen esta forma:

    {"error": {"codigo": "not_found", "mensaje": "No encontrado."}}

y, en los errores de validación de varios campos, además "campos":

    {"error": {"codigo": "datos_invalidos",
               "mensaje": "Hay datos inválidos. Revisa los campos.",
               "campos": {"email": ["Ya existe un usuario con este correo."]}}}

Las vistas no arman respuestas de error a mano: lanzan las excepciones de DRF
(ValidationError, NotFound, PermissionDenied...) y este manejador les da formato.
"""
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.views import exception_handler

MENSAJE_CAMPOS_INVALIDOS = "Hay datos inválidos. Revisa los campos."


def manejador_errores(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        # Error no controlado (500): lo maneja Django como siempre.
        return None

    # DRF convierte estos dos errores de Django en sus propias excepciones.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response.data = {"error": _armar_error(exc)}
    return response


def _armar_error(exc):
    detalle = exc.detail
    codigo_por_defecto = exc.default_code

    if isinstance(detalle, dict):
        # Errores con un solo mensaje general, por ejemplo:
        #   ValidationError({"detail": "..."}) o los tokens inválidos de SimpleJWT,
        #   que llegan como {"detail": "...", "code": "token_not_valid", "messages": [...]}
        if "detail" in detalle:
            codigo = detalle.get("code") or _codigo(detalle["detail"], codigo_por_defecto)
            return {"codigo": str(codigo), "mensaje": _mensaje(detalle["detail"])}
        if set(detalle) == {"non_field_errors"}:
            errores = detalle["non_field_errors"]
            return {
                "codigo": _codigo(errores, codigo_por_defecto),
                "mensaje": _mensaje(errores),
            }
        # Errores de validación por campo.
        return {
            "codigo": "datos_invalidos",
            "mensaje": MENSAJE_CAMPOS_INVALIDOS,
            "campos": detalle,
        }

    return {"codigo": _codigo(detalle, codigo_por_defecto), "mensaje": _mensaje(detalle)}


def _mensaje(detalle):
    if isinstance(detalle, list):
        return " ".join(str(item) for item in detalle)
    return str(detalle)


def _codigo(detalle, por_defecto):
    if isinstance(detalle, list) and detalle:
        detalle = detalle[0]
    return str(getattr(detalle, "code", None) or por_defecto)