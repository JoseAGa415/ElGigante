# Generated manually on 2026-01-21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beneficio', '0035_add_beneficiado_finca_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='bodega',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='bodega',
            name='nombre',
            field=models.CharField(default='Bodega', max_length=100),
        ),
        migrations.AlterField(
            model_name='bodega',
            name='responsable',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bodegas', to=settings.AUTH_USER_MODEL),
        ),
    ]
