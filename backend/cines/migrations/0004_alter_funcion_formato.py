from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cines", "0003_ejecucionscraping"),
    ]

    operations = [
        migrations.AlterField(
            model_name="funcion",
            name="formato",
            field=models.CharField(blank=True, max_length=150),
        ),
    ]