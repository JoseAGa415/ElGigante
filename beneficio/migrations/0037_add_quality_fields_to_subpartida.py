# Generated manually on 2026-01-23 - Add quality fields to SubPartida

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beneficio', '0036_add_nombre_activo_to_bodega'),
    ]

    operations = [
        # Nuevos campos de calidad para SubPartida
        migrations.AddField(
            model_name='subpartida',
            name='tipo_proceso',
            field=models.CharField(choices=[('LAVADO', 'Lavado'), ('NATURAL', 'Natural'), ('HONEY', 'Honey'), ('LADADO', 'Ladado'), ('LAVADO 2 LATAS', 'Lavado 2 Latas')], default='LAVADO', help_text='Tipo de proceso del café', max_length=20),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='quintales',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Cantidad en quintales (qq)', max_digits=10),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='rendimiento_b15',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Rendimiento b/15', max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='defectos',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Porcentaje de defectos', max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='rb',
            field=models.DecimalField(blank=True, decimal_places=4, help_text='RB', max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='rn',
            field=models.DecimalField(blank=True, decimal_places=4, help_text='RN', max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='score',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Puntaje de catación (SCORD)', max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='taza',
            field=models.CharField(blank=True, choices=[('SANA LIMPIA', 'Sana Limpia'), ('LIMPIA', 'Limpia'), ('REGULAR', 'Regular'), ('DEFECTUOSA', 'Defectuosa')], help_text='Calidad de taza', max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='subpartida',
            name='cualidades',
            field=models.TextField(blank=True, help_text='Cualidades del café (sabores, aromas)', null=True),
        ),
    ]
