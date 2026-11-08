from django.db import migrations, models


class Migration(migrations.Migration):
    """Paso 3: ya sin correos vacíos repetidos, el correo pasa a ser único."""

    dependencies = [
        ("usuarios", "0003_emails_vacios_a_null"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usuario",
            name="email",
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                unique=True,
                verbose_name="correo electrónico",
            ),
        ),
    ]