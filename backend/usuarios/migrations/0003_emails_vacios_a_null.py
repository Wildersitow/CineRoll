from django.db import migrations


def vacios_a_null(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    Usuario.objects.filter(email="").update(email=None)


def null_a_vacios(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    Usuario.objects.filter(email__isnull=True).update(email="")


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_avatar_biografia_email_opcional'),
    ]

    operations = [
        migrations.RunPython(vacios_a_null, null_a_vacios),
    ]
