from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='avatar',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='biografia',
            field=models.TextField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='correo electrónico'),
        ),
    ]
