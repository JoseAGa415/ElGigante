from django.core.management.base import BaseCommand
from django.db import connection, transaction
from beneficio.models import Partida


class Command(BaseCommand):
    help = 'Reinicia los IDs y numeros de partidas activas de forma secuencial (1, 2, 3...)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar que deseas ejecutar esta operacion',
        )

    def handle(self, *args, **options):
        db_engine = connection.vendor

        # Solo partidas activas
        partidas = list(Partida.objects.filter(activo=True).order_by('fecha_creacion', 'id'))
        inactivas_count = Partida.objects.filter(activo=False).count()

        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                f'\nADVERTENCIA: Esta operacion renumerara las partidas ACTIVAS.\n'
                f'   Base de datos detectada: {db_engine}\n'
                f'   Partidas activas a renumerar: {len(partidas)}\n'
                f'   Partidas inactivas (ignoradas): {inactivas_count}\n\n'
                f'   Para ejecutar, usa: python manage.py reset_partida_ids --confirm\n'
            ))
            self.stdout.write('\nPartidas activas actuales:')
            self.stdout.write('-' * 50)
            for p in partidas:
                self.stdout.write(f'  ID: {p.id:3} | {p.numero_partida} | {p.nombre}')
            self.stdout.write('-' * 50)
            return

        if not partidas:
            self.stdout.write(self.style.WARNING('No hay partidas activas para resetear.'))
            return

        self.stdout.write(f'\nIniciando reset de {len(partidas)} partidas activas... (DB: {db_engine})\n')

        try:
            with transaction.atomic():
                # Mapeo: ID actual -> ID nuevo secuencial
                id_mapping = {}
                for new_id, partida in enumerate(partidas, start=1):
                    id_mapping[partida.id] = new_id
                    self.stdout.write(f'  {partida.numero_partida}: ID {partida.id} -> ID {new_id}')

                # Paso 1: IDs temporales negativos para evitar conflictos
                self.stdout.write('\nPaso 1: IDs temporales...')
                with connection.cursor() as cursor:
                    for old_id in id_mapping.keys():
                        temp_id = -old_id
                        if db_engine == 'postgresql':
                            cursor.execute('UPDATE subpartidas SET partida_id = %s WHERE partida_id = %s', [temp_id, old_id])
                            cursor.execute('UPDATE partidas SET id = %s WHERE id = %s', [temp_id, old_id])
                        else:
                            cursor.execute('UPDATE subpartidas SET partida_id = ? WHERE partida_id = ?', [temp_id, old_id])
                            cursor.execute('UPDATE partidas SET id = ? WHERE id = ?', [temp_id, old_id])

                # Paso 2: IDs finales
                self.stdout.write('Paso 2: IDs finales...')
                with connection.cursor() as cursor:
                    for old_id, new_id in id_mapping.items():
                        temp_id = -old_id
                        if db_engine == 'postgresql':
                            cursor.execute('UPDATE partidas SET id = %s WHERE id = %s', [new_id, temp_id])
                            cursor.execute('UPDATE subpartidas SET partida_id = %s WHERE partida_id = %s', [new_id, temp_id])
                        else:
                            cursor.execute('UPDATE partidas SET id = ? WHERE id = ?', [new_id, temp_id])
                            cursor.execute('UPDATE subpartidas SET partida_id = ? WHERE partida_id = ?', [new_id, temp_id])

                # Paso 3: Resetear secuencia al maximo ID existente (activas + inactivas)
                self.stdout.write('Paso 3: Reseteando secuencia...')
                max_id_total = Partida.objects.order_by('-id').values_list('id', flat=True).first() or len(partidas)
                with connection.cursor() as cursor:
                    if db_engine == 'postgresql':
                        cursor.execute(
                            "SELECT setval(pg_get_serial_sequence('partidas', 'id'), %s, true)",
                            [max_id_total]
                        )
                    else:
                        cursor.execute(
                            'UPDATE sqlite_sequence SET seq = ? WHERE name = ?',
                            [max_id_total, 'partidas']
                        )

                # Paso 4: Actualizar numero_partida (PAR-0001, PAR-0002, ...)
                self.stdout.write('Paso 4: Actualizando numero_partida...')
                with connection.cursor() as cursor:
                    for new_id, partida in enumerate(partidas, start=1):
                        nuevo_numero = f'PAR-{new_id:04d}'
                        if db_engine == 'postgresql':
                            cursor.execute('UPDATE partidas SET numero_partida = %s WHERE id = %s', [nuevo_numero, new_id])
                        else:
                            cursor.execute('UPDATE partidas SET numero_partida = ? WHERE id = ?', [nuevo_numero, new_id])
                        self.stdout.write(f'  {partida.numero_partida} -> {nuevo_numero}')

                self.stdout.write(self.style.SUCCESS(f'\nReset completado exitosamente!'))
                self.stdout.write(f'   - {len(partidas)} partidas activas renumeradas')
                self.stdout.write(f'   - La proxima partida nueva sera PAR-{len(partidas) + 1:04d}\n')

                self.stdout.write('\nEstado final:')
                self.stdout.write('-' * 50)
                for p in Partida.objects.filter(activo=True).order_by('id'):
                    self.stdout.write(f'  ID: {p.id:3} | {p.numero_partida} | {p.nombre} | Subs: {p.subpartidas.count()}')
                self.stdout.write('-' * 50)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError: {str(e)}'))
            self.stdout.write('   La operacion ha sido revertida (rollback).')
            raise
