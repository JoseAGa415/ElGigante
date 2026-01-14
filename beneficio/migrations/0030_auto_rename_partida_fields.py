# Generated manually on 2026-01-14
# Renombrar campos del modelo Partida

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('beneficio', '0029_fix_partidas'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Eliminar campos antiguos y crear nuevos con la estructura correcta
        migrations.RemoveField(
            model_name='partida',
            name='tipo_cafe',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='proveedor',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='fecha_ingreso',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='peso_bruto_kg',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='tara_kg',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='peso_neto_kg',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='unidad_peso',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='humedad',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='numero_sacos',
        ),
        migrations.RemoveField(
            model_name='partida',
            name='lote',
        ),

        # Renombrar campos de fecha
        migrations.RenameField(
            model_name='partida',
            old_name='created_at',
            new_name='fecha_creacion',
        ),
        migrations.RenameField(
            model_name='partida',
            old_name='updated_at',
            new_name='fecha_modificacion',
        ),
        migrations.RenameField(
            model_name='partida',
            old_name='created_by',
            new_name='creado_por',
        ),

        # Agregar nuevos campos
        migrations.AddField(
            model_name='partida',
            name='nombre',
            field=models.CharField(default='Sin nombre', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='partida',
            name='descripcion',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='partida',
            name='percha',
            field=models.CharField(blank=True, help_text='Nombre de la percha', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='partida',
            name='peso_total_kg',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
        migrations.AddField(
            model_name='partida',
            name='numero_subpartidas',
            field=models.IntegerField(default=0, editable=False),
        ),

        # Modificar campo bodega
        migrations.AlterField(
            model_name='partida',
            name='bodega',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='partidas_ubicadas', to='beneficio.bodega'),
        ),

        # Modificar opciones del modelo
        migrations.AlterModelOptions(
            name='partida',
            options={'ordering': ['-fecha_creacion'], 'verbose_name': 'Partida', 'verbose_name_plural': 'Partidas'},
        ),

        # Cambiar nombre de tabla
        migrations.AlterModelTable(
            name='partida',
            table='partidas',
        ),

        # Crear modelo SubPartida
        migrations.CreateModel(
            name='SubPartida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_subpartida', models.CharField(editable=False, max_length=50, unique=True)),
                ('nombre', models.CharField(max_length=200)),
                ('fila', models.CharField(blank=True, help_text='Fila en la percha', max_length=50, null=True)),
                ('peso_bruto_kg', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tara_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('peso_neto_kg', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('unidad_medida', models.CharField(default='kg', max_length=10)),
                ('fecha_ingreso', models.DateTimeField(blank=True, null=True)),
                ('proveedor', models.CharField(blank=True, max_length=200, null=True)),
                ('numero_sacos', models.IntegerField(blank=True, null=True)),
                ('humedad', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('creado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subpartidas_creadas', to=settings.AUTH_USER_MODEL)),
                ('partida', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subpartidas', to='beneficio.partida')),
            ],
            options={
                'verbose_name': 'Sub-Partida',
                'verbose_name_plural': 'Sub-Partidas',
                'db_table': 'subpartidas',
                'ordering': ['numero_subpartida'],
            },
        ),
    ]
