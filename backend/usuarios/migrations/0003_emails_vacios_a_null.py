from django.db import migrations


def vacios_a_null(apps, schema_editor):
    """Los usuarios sin correo pasan de "" a NULL para no chocar con el unique."""
    Usuario = apps.get_model("usuarios", "Usuario")
    Usuario.objects.filter(email="").update(email=None)


def null_a_vacios(apps, schema_editor):
    """Reversa: si se deshace la migración, NULL vuelve a ser ""."""
    Usuario = apps.get_model("usuarios", "Usuario")
    Usuario.objects.filter(email__isnull=True).update(email="")


class Migration(migrations.Migration):
    """Paso 2: limpieza de datos, en su propia migración."""

    dependencies = [
        ("usuarios", "0002_perfil_y_correo_opcional"),
    ]

    operations = [
        migrations.RunPython(vacios_a_null, null_a_vacios),
    ]