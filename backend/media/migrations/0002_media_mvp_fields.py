from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("media", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="media",
            name="titulo_original",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="media",
            name="duracion",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="media",
            name="poster_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="media",
            name="trailer_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="media",
            name="estado",
            field=models.CharField(
                choices=[
                    ("en_cartelera", "En cartelera"),
                    ("proximo_estreno", "Próximo estreno"),
                    ("fuera_cartelera", "Fuera de cartelera"),
                ],
                default="proximo_estreno",
                max_length=20,
            ),
        ),
    ]