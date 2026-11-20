from django.conf import settings
from django.db import migrations


def crear_listas_sistema(apps, schema_editor):
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    Usuario = apps.get_model(user_app, user_model)
    Lista = apps.get_model("social", "Lista")

    for usuario in Usuario.objects.all():
        if not Lista.objects.filter(usuario=usuario, tipo="favoritas").exists():
            Lista.objects.create(
                usuario=usuario,
                nombre="Favoritas",
                tipo="favoritas",
                publica=True,
            )
        if not Lista.objects.filter(usuario=usuario, tipo="por_ver").exists():
            Lista.objects.create(
                usuario=usuario,
                nombre="Por ver",
                tipo="por_ver",
                publica=True,
            )


def revertir_listas_sistema(apps, schema_editor):
    Lista = apps.get_model("social", "Lista")
    Lista.objects.filter(tipo__in=["favoritas", "por_ver"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0005_sugerencia_valor_anterior"),
    ]

    operations = [
        migrations.RunPython(crear_listas_sistema, revertir_listas_sistema),
    ]
