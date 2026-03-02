from django.core.management.base import BaseCommand
from django.db import connection, transaction
from beneficio.models import Partida, SubPartida


class Command(BaseCommand):
    help = 'Reinicia los IDs de las partidas para que sean secuenciales (1, 2, 3...)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar que deseas ejecutar esta operacion',
        )

    def handle(self, *args, **options):
        # Detectar el tipo de base de datos
        db_engine = connection.vendor  # 'sqlite', 'postgresql', 'mysql', etc.

        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                f'\nADVERTENCIA: Esta operacion modificara los IDs de las partidas.\n'
                f'   Base de datos detectada: {db_engine}\n'
                f'   Asegurate de tener un backup de la base de datos.\n\n'
                f'   Para ejecutar, usa: python manage.py reset_partida_ids --confirm\n'
            ))

            # Mostrar estado actual
            partidas = Partida.objects.all().order_by('id')
            self.stdout.write('\nEstado actual de las partidas:')
            self.stdout.write('-' * 50)
            for p in partidas:
                subpartidas_count = p.subpartidas.count()
                self.stdout.write(f'  ID: {p.id:3} | {p.numero_partida} | {p.nombre} | SubPartidas: {subpartidas_count}')
            self.stdout.write('-' * 50)
            self.stdout.write(f'Total: {partidas.count()} partidas\n')
            return

        # Ejecutar el reset
        self.stdout.write(f'\nIniciando reset de IDs... (DB: {db_engine})\n')

        try:
            with transaction.atomic():
                # Obtener todas las partidas ordenadas por fecha de creacion o ID actual
                partidas = list(Partida.objects.all().order_by('fecha_creacion', 'id'))

                if not partidas:
                    self.stdout.write(self.style.WARNING('No hay partidas para resetear.'))
                    return

                self.stdout.write(f'Procesando {len(partidas)} partidas...\n')

                # Crear mapeo de ID antiguo a ID nuevo
                id_mapping = {}
                for new_id, partida in enumerate(partidas, start=1):
                    id_mapping[partida.id] = new_id
                    self.stdout.write(f'  {partida.numero_partida}: ID {partida.id} -> ID {new_id}')

                # Paso 1: IDs temporales negativos para evitar conflictos
                self.stdout.write('\nPaso 1: Asignando IDs temporales...')
                with connection.cursor() as cursor:
                    for old_id, new_id in id_mapping.items():
                        temp_id = -old_id
                        if db_engine == 'postgresql':
                            cursor.execute(
                                'UPDATE subpartidas SET partida_id = %s WHERE partida_id = %s',
                                [temp_id, old_id]
                            )
                            cursor.execute(
                                'UPDATE partidas SET id = %s WHERE id = %s',
                                [temp_id, old_id]
                            )
                        else:  # SQLite
                            cursor.execute(
                                'UPDATE subpartidas SET partida_id = ? WHERE partida_id = ?',
                                [temp_id, old_id]
                            )
                            cursor.execute(
                                'UPDATE partidas SET id = ? WHERE id = ?',
                                [temp_id, old_id]
                            )

                # Paso 2: IDs finales
                self.stdout.write('Paso 2: Asignando IDs finales...')
                with connection.cursor() as cursor:
                    for old_id, new_id in id_mapping.items():
                        temp_id = -old_id
                        if db_engine == 'postgresql':
                            cursor.execute(
                                'UPDATE partidas SET id = %s WHERE id = %s',
                                [new_id, temp_id]
                            )
                            cursor.execute(
                                'UPDATE subpartidas SET partida_id = %s WHERE partida_id = %s',
                                [new_id, temp_id]
                            )
                        else:  # SQLite
                            cursor.execute(
                                'UPDATE partidas SET id = ? WHERE id = ?',
                                [new_id, temp_id]
                            )
                            cursor.execute(
                                'UPDATE subpartidas SET partida_id = ? WHERE partida_id = ?',
                                [new_id, temp_id]
                            )

                # Paso 3: Resetear secuencia de autoincremento
                self.stdout.write('Paso 3: Reseteando secuencia de autoincremento...')
                max_id = len(partidas)
                with connection.cursor() as cursor:
                    if db_engine == 'postgresql':
                        cursor.execute(
                            "SELECT setval(pg_get_serial_sequence('partidas', 'id'), %s, true)",
                            [max_id]
                        )
                    else:  # SQLite
                        cursor.execute(
                            'UPDATE sqlite_sequence SET seq = ? WHERE name = ?',
                            [max_id, 'partidas']
                        )

                # Paso 4: Actualizar campo numero_partida (PAR-0001, PAR-0002, ...)
                self.stdout.write('Paso 4: Actualizando numero_partida...')
                with connection.cursor() as cursor:
                    for new_id, partida in enumerate(partidas, start=1):
                        nuevo_numero = f'PAR-{new_id:04d}'
                        if db_engine == 'postgresql':
                            cursor.execute(
                                'UPDATE partidas SET numero_partida = %s WHERE id = %s',
                                [nuevo_numero, new_id]
                            )
                        else:
                            cursor.execute(
                                'UPDATE partidas SET numero_partida = ? WHERE id = ?',
                                [nuevo_numero, new_id]
                            )
                        self.stdout.write(f'  {partida.numero_partida} -> {nuevo_numero}')

                self.stdout.write(self.style.SUCCESS(f'\nReset completado exitosamente!'))
                self.stdout.write(f'   - {len(partidas)} partidas renumeradas')
                self.stdout.write(f'   - Secuencia reiniciada a {max_id}')
                self.stdout.write(f'   - La proxima partida tendra ID {max_id + 1}\n')

                # Mostrar resultado final
                self.stdout.write('\nNuevo estado de las partidas:')
                self.stdout.write('-' * 50)
                for p in Partida.objects.all().order_by('id'):
                    subpartidas_count = p.subpartidas.count()
                    self.stdout.write(f'  ID: {p.id:3} | {p.numero_partida} | {p.nombre} | SubPartidas: {subpartidas_count}')
                self.stdout.write('-' * 50)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError: {str(e)}'))
            self.stdout.write('   La operacion ha sido revertida (rollback).')
            raise
