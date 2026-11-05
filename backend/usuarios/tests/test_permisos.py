from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from usuarios.permissions import (
    EsAdministrador,
    EsAdministradorOLecturaPublica,
    EsAutorOLecturaPublica,
)

factory = APIRequestFactory()


def peticion(metodo, usuario):
    request = getattr(factory, metodo)("/")
    request.user = usuario
    return request


VISITANTE = AnonymousUser()
USUARIO = SimpleNamespace(pk=1, is_authenticated=True, is_staff=False)
OTRO = SimpleNamespace(pk=2, is_authenticated=True, is_staff=False)
ADMIN = SimpleNamespace(pk=3, is_authenticated=True, is_staff=True)


class EsAdministradorTests(SimpleTestCase):
    def test_solo_staff(self):
        permiso = EsAdministrador()
        self.assertFalse(permiso.has_permission(peticion("get", VISITANTE), None))
        self.assertFalse(permiso.has_permission(peticion("get", USUARIO), None))
        self.assertTrue(permiso.has_permission(peticion("get", ADMIN), None))


class EsAdministradorOLecturaPublicaTests(SimpleTestCase):
    def test_lectura_abierta_y_escritura_solo_staff(self):
        permiso = EsAdministradorOLecturaPublica()
        self.assertTrue(permiso.has_permission(peticion("get", VISITANTE), None))
        self.assertFalse(permiso.has_permission(peticion("post", VISITANTE), None))
        self.assertFalse(permiso.has_permission(peticion("post", USUARIO), None))
        self.assertTrue(permiso.has_permission(peticion("post", ADMIN), None))


class EsAutorOLecturaPublicaTests(SimpleTestCase):
    def setUp(self):
        self.permiso = EsAutorOLecturaPublica()
        self.objeto = SimpleNamespace(usuario_id=USUARIO.pk, dueno_id=USUARIO.pk)
        self.vista = SimpleNamespace()

    def test_lectura_publica(self):
        request = peticion("get", VISITANTE)
        self.assertTrue(self.permiso.has_permission(request, self.vista))
        self.assertTrue(self.permiso.has_object_permission(request, self.vista, self.objeto))

    def test_escribir_exige_sesion(self):
        self.assertFalse(self.permiso.has_permission(peticion("post", VISITANTE), self.vista))
        self.assertTrue(self.permiso.has_permission(peticion("post", USUARIO), self.vista))

    def test_solo_el_autor_modifica_su_objeto(self):
        for metodo in ("put", "patch", "delete"):
            with self.subTest(metodo=metodo):
                self.assertTrue(
                    self.permiso.has_object_permission(peticion(metodo, USUARIO), self.vista, self.objeto)
                )
                self.assertFalse(
                    self.permiso.has_object_permission(peticion(metodo, OTRO), self.vista, self.objeto)
                )

    def test_el_campo_del_autor_se_puede_configurar(self):
        vista = SimpleNamespace(campo_autor="dueno")
        self.assertTrue(self.permiso.has_object_permission(peticion("patch", USUARIO), vista, self.objeto))
        self.assertFalse(self.permiso.has_object_permission(peticion("patch", OTRO), vista, self.objeto))
