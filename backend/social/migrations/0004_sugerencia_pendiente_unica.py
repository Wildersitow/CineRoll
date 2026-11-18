from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0003_reporteresena"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="sugerenciaedicion",
            constraint=models.UniqueConstraint(
                condition=models.Q(("estado", "pendiente")),
                fields=("usuario", "media", "campo"),
                name="social_sugerencia_pendiente_unica",
            ),
        ),
    ]
