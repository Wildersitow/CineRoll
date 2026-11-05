from django.db import migrations, models


class Migration(migrations.Migration):
    """Si falla aquí es porque hay correos repetidos en la tabla: corrígelos a mano
    (desde el admin o el shell) y vuelve a ejecutar `migrate`."""

    dependencies = [
        ('usuarios', '0003_emails_vacios_a_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name='correo electrónico'),
        ),
    ]
