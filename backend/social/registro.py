"""Estado de un título para un usuario: visto, viendo, pendiente y me gusta.

"Pendiente" es estar en la lista Por ver, así que el perfil y la lista siguen
siendo la misma fuente de verdad. Marcar un título como visto (o reseñarlo) lo
saca de Por ver, igual que en Letterboxd.
"""

from django.db import transaction
from django.db.models import Max

from social.models import ElementoLista, Lista, RegistroTitulo


def lista_por_ver(usuario):
    lista, _ = Lista.objects.get_or_create(
        usuario=usuario,
        tipo=Lista.Tipo.POR_VER,
        defaults={"nombre": "Por ver", "publica": True},
    )
    return lista


def esta_pendiente(usuario, media):
    return ElementoLista.objects.filter(
        lista__usuario=usuario, lista__tipo=Lista.Tipo.POR_VER, media=media
    ).exists()


def marcar_pendiente(usuario, media, pendiente):
    lista = lista_por_ver(usuario)
    if not pendiente:
        ElementoLista.objects.filter(lista=lista, media=media).delete()
        return
    if ElementoLista.objects.filter(lista=lista, media=media).exists():
        return
    ultimo = lista.elementos_lista.aggregate(maximo=Max("orden"))["maximo"]
    ElementoLista.objects.get_or_create(
        lista=lista, media=media, defaults={"orden": 0 if ultimo is None else ultimo + 1}
    )


def datos_registro(usuario, media):
    registro = RegistroTitulo.objects.filter(usuario=usuario, media=media).first()
    return {
        "media_id": media.id,
        "estado": registro.estado if registro else "",
        "me_gusta": registro.me_gusta if registro else False,
        "pendiente": esta_pendiente(usuario, media),
    }


@transaction.atomic
def actualizar_registro(usuario, media, cambios):
    """Aplica los campos presentes en `cambios` (estado, me_gusta, pendiente)."""
    if "estado" in cambios or "me_gusta" in cambios:
        registro, _ = RegistroTitulo.objects.select_for_update().get_or_create(
            usuario=usuario, media=media
        )
        if "estado" in cambios:
            registro.estado = cambios["estado"]
        if "me_gusta" in cambios:
            registro.me_gusta = cambios["me_gusta"]
        registro.save()
        if registro.estado == RegistroTitulo.Estado.VISTO and "pendiente" not in cambios:
            marcar_pendiente(usuario, media, False)
    if "pendiente" in cambios:
        marcar_pendiente(usuario, media, cambios["pendiente"])
    return datos_registro(usuario, media)


def registrar_resena(usuario, media):
    """Al reseñar, el título pasa a visto (salvo que se esté viendo) y sale de Por ver."""
    registro, _ = RegistroTitulo.objects.get_or_create(usuario=usuario, media=media)
    if registro.estado != RegistroTitulo.Estado.VIENDO:
        registro.estado = RegistroTitulo.Estado.VISTO
        registro.save(update_fields=["estado", "fecha_actualizacion"])
    marcar_pendiente(usuario, media, False)
