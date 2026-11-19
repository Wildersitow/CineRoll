from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0004_sugerencia_pendiente_unica"),
    ]

    operations = [
        migrations.AddField(
            model_name="sugerenciaedicion",
            name="valor_anterior",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Valor que tenía el campo antes de aprobar la sugerencia.",
            ),
        ),
    ]
