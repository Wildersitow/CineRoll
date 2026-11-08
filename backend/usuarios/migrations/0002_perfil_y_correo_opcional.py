from django.db import migrations, models


class Migration(migrations.Migration):
    """Paso 1: campos del perfil y correo que acepta NULL (todavía sin unique)."""

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="avatar",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="usuario",
            name="biografia",
            field=models.TextField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="usuario",
            name="escala_calificacion",
            field=models.PositiveSmallIntegerField(
                choices=[(5, "5 estrellas (con medias)"), (10, "1 a 10 puntos")],
                default=10,
            ),
        ),
        migrations.AlterField(
            model_name="usuario",
            name="email",
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                verbose_name="correo electrónico",
            ),
        ),
    ]