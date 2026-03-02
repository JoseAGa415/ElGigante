from django.core.management.base import BaseCommand
from django.db import connection, transaction
from beneficio.models import Partida


class Command(BaseCommand):
    help = 'Elimina partidas inactivas y renumera las activas desde PAR-0001'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar que deseas ejecutar esta operacion',
        )

    def handle(self, *args, **options):
        db_engine = connection.vendor

        activas = list(Partida.objects.filter(activo=True).order_by('fecha_creacion', 'id'))
        inactivas = list(Partida.objects.filter(activo=False).order_by('id'))

        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                f'\nADVERTENCIA: Esta operacion:\n'
                f'   1) Eliminara permanentemente {len(inactivas)} partidas inactivas\n'
                f'   2) Renumerara {len(activas)} partidas activas desde PAR-0001\n'
                f'   Base de datos: {db_engine}\n\n'
                f'   Para ejecutar: python manage.py reset_partida_ids --confirm\n'
            ))
            self.stdout.write('\nPartidas activas:')
            self.stdout.write('-' * 50)
            for p in activas:
                self.stdout.write(f'  ID: {p.id:3} | {p.numero_partida} | {p.nombre}')
            self.stdout.write(f'\nPartidas inactivas a eliminar: {len(inactivas)}')
            self.stdout.write('-' * 50)
            return

        if not activas:
            self.stdout.write(self.style.WARNING('No hay partidas activas para resetear.'))
            return

        self.stdout.write(f'\nIniciando reset... (DB: {db_engine})\n')

        try:
            with transaction.atomic():
                # Paso 1: Eliminar permanentemente las inactivas y sus subpartidas
                if inactivas:
                    self.stdout.write(f'Paso 1: Eliminando {len(inactivas)} partidas inactivas...')
                    ids_inactivas = [p.id for p in inactivas]
                    with connection.cursor() as cursor:
                        if db_engine == 'postgresql':
                            cursor.execute(
                                'DELETE FROM subpartidas WHERE partida_id = ANY(%s)',
                                [ids_inactivas]
                            )
                            cursor.execute(
                                'DELETE FROM partidas WHERE id = ANY(%s)',
                                [ids_inactivas]
                            )
                        else:
                            placeholders = ','.join(['?' for _ in ids_inactivas])
                            cursor.execute(f'DELETE FROM subpartidas WHERE partida_id IN ({placeholders})', ids_inactivas)
                            cursor.execute(f'DELETE FROM partidas WHERE id IN ({placeholders})', ids_inactivas)
                    self.stdout.write(f'  {len(inactivas)} partidas inactivas eliminadas.')
                else:
                    self.stdout.write('Paso 1: No hay partidas inactivas.')

                # Paso 2: IDs temporales negativos para las activas
                self.stdout.write('Paso 2: IDs temporales...')
                with connection.cursor() as cursor:
                    for partida in activas:
                        temp_id = -partida.id
                        if db_engine == 'postgresql':
                            cursor.execute('UPDATE subpartidas SET partida_id = %s WHERE partida_id = %s', [temp_id, partida.id])
                            cursor.execute('UPDATE partidas SET id = %s WHERE id = %s', [temp_id, partida.id])
                        else:
                            cursor.execute('UPDATE subpartidas SET partida_id = ? WHERE partida_id = ?', [temp_id, partida.id])
                            cursor.execute('UPDATE partidas SET id = ? WHERE id = ?', [temp_id, partida.id])

                # Paso 3: IDs finales secuenciales
                self.stdout.write('Paso 3: IDs finales...')
                with connection.cursor() as cursor:
                    for new_id, partida in enumerate(activas, start=1):
                        temp_id = -partida.id
                        if db_engine == 'postgresql':
                            cursor.execute('UPDATE partidas SET id = %s WHERE id = %s', [new_id, temp_id])
                            cursor.execute('UPDATE subpartidas SET partida_id = %s WHERE partida_id = %s', [new_id, temp_id])
                        else:
                            cursor.execute('UPDATE partidas SET id = ? WHERE id = ?', [new_id, temp_id])
                            cursor.execute('UPDATE subpartidas SET partida_id = ? WHERE partida_id = ?', [new_id, temp_id])

                # Paso 4: Resetear secuencia al total de activas
                self.stdout.write('Paso 4: Reseteando secuencia...')
                max_id = len(activas)
                with connection.cursor() as cursor:
                    if db_engine == 'postgresql':
                        cursor.execute(
                            "SELECT setval(pg_get_serial_sequence('partidas', 'id'), %s, true)",
                            [max_id]
                        )
                    else:
                        cursor.execute(
                            'UPDATE sqlite_sequence SET seq = ? WHERE name = ?',
                            [max_id, 'partidas']
                        )

                # Paso 5: Actualizar numero_partida y numero_subpartida
                self.stdout.write('Paso 5: Actualizando numero_partida y subpartidas...')
                with connection.cursor() as cursor:
                    for new_id, partida in enumerate(activas, start=1):
                        nuevo_numero = f'PAR-{new_id:04d}'
                        viejo_numero = partida.numero_partida
                        if db_engine == 'postgresql':
                            cursor.execute('UPDATE partidas SET numero_partida = %s WHERE id = %s', [nuevo_numero, new_id])
                            # Actualizar numero_subpartida: reemplazar prefijo viejo por nuevo
                            cursor.execute(
                                "UPDATE subpartidas SET numero_subpartida = %s || substring(numero_subpartida from length(%s)+1) WHERE partida_id = %s AND numero_subpartida LIKE %s",
                                [nuevo_numero, viejo_numero, new_id, f'{viejo_numero}%']
                            )
                        else:
                            cursor.execute('UPDATE partidas SET numero_partida = ? WHERE id = ?', [nuevo_numero, new_id])
                            cursor.execute(
                                "UPDATE subpartidas SET numero_subpartida = ? || substr(numero_subpartida, length(?)+1) WHERE partida_id = ? AND numero_subpartida LIKE ?",
                                [nuevo_numero, viejo_numero, new_id, f'{viejo_numero}%']
                            )
                        self.stdout.write(f'  {viejo_numero} -> {nuevo_numero}')

                self.stdout.write(self.style.SUCCESS(f'\nReset completado!'))
                self.stdout.write(f'   - {len(activas)} partidas renumeradas')
                self.stdout.write(f'   - La proxima partida nueva sera PAR-{len(activas) + 1:04d}\n')

                self.stdout.write('Estado final:')
                self.stdout.write('-' * 50)
                for p in Partida.objects.filter(activo=True).order_by('id'):
                    self.stdout.write(f'  ID: {p.id:3} | {p.numero_partida} | {p.nombre}')
                self.stdout.write('-' * 50)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError: {str(e)}'))
            self.stdout.write('   Operacion revertida (rollback).')
            raise
