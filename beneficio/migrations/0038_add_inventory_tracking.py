# Generated manually on 2026-01-26 - Add inventory tracking to SubPartida

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('beneficio', '0037_add_quality_fields_to_subpartida'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Agregar campo estado a SubPartida
        migrations.AddField(
            model_name='subpartida',
            name='estado',
            field=models.CharField(
                choices=[
                    ('DISPONIBLE', 'Disponible'),
                    ('PARCIAL', 'Parcialmente Procesado'),
                    ('PROCESADO', 'Completamente Procesado'),
                    ('AGOTADO', 'Agotado'),
                ],
                default='DISPONIBLE',
                help_text='Estado de inventario',
                max_length=20,
            ),
        ),
        # Crear tabla MovimientoSubPartida
        migrations.CreateModel(
            name='MovimientoSubPartida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_destino', models.CharField(
                    choices=[
                        ('PROCESADO', 'Procesado/Trilla'),
                        ('REPROCESO', 'Reproceso'),
                        ('MEZCLA', 'Mezcla'),
                        ('VENTA', 'Venta Directa'),
                        ('AJUSTE', 'Ajuste de Inventario'),
                    ],
                    help_text='Tipo de proceso destino',
                    max_length=20,
                )),
                ('quintales_movidos', models.DecimalField(
                    decimal_places=2,
                    help_text='Cantidad en quintales (qq) movidos',
                    max_digits=10,
                )),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('creado_por', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='movimientos_creados',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('mezcla', models.ForeignKey(
                    blank=True,
                    help_text='Mezcla destino',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='movimientos_subpartida',
                    to='beneficio.mezcla',
                )),
                ('procesado', models.ForeignKey(
                    blank=True,
                    help_text='Procesado/Trilla destino',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='movimientos_subpartida',
                    to='beneficio.procesado',
                )),
                ('reproceso', models.ForeignKey(
                    blank=True,
                    help_text='Reproceso destino',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='movimientos_subpartida',
                    to='beneficio.reproceso',
                )),
                ('subpartida', models.ForeignKey(
                    help_text='SubPartida de origen',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='movimientos',
                    to='beneficio.subpartida',
                )),
            ],
            options={
                'verbose_name': 'Movimiento de SubPartida',
                'verbose_name_plural': 'Movimientos de SubPartidas',
                'db_table': 'movimientos_subpartida',
                'ordering': ['-fecha'],
            },
        ),
    ]
