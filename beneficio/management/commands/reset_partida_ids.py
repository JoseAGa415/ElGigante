from django.core.management.base import BaseCommand
from django.db import connection, transaction
from beneficio.models import Partida, SubPartida


class Command(BaseCommand):
    help = 'Reinicia los IDs de las partidas para que sean secuenciales (1, 2, 3...)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar que deseas ejecutar esta operación',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  ADVERTENCIA: Esta operación modificará los IDs de las partidas.\n'
                '   Asegúrate de tener un backup de la base de datos.\n\n'
                '   Para ejecutar, usa: python manage.py reset_partida_ids --confirm\n'
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
        self.stdout.write('\n🔄 Iniciando reset de IDs...\n')

        try:
            with transaction.atomic():
                # Obtener todas las partidas ordenadas por fecha de creación o ID actual
                partidas = list(Partida.objects.all().order_by('fecha_creacion', 'id'))

                if not partidas:
                    self.stdout.write(self.style.WARNING('No hay partidas para resetear.'))
                    return

                self.stdout.write(f'📋 Procesando {len(partidas)} partidas...\n')

                # Crear mapeo de ID antiguo a ID nuevo
                id_mapping = {}
                for new_id, partida in enumerate(partidas, start=1):
                    id_mapping[partida.id] = new_id
                    self.stdout.write(f'  {partida.numero_partida}: ID {partida.id} → ID {new_id}')

                # Usar IDs temporales para evitar conflictos de unicidad
                # Primero movemos todos a IDs negativos temporales
                self.stdout.write('\n🔧 Paso 1: Asignando IDs temporales...')
                with connection.cursor() as cursor:
                    for old_id, new_id in id_mapping.items():
                        temp_id = -old_id  # ID temporal negativo
                        # Actualizar subpartidas primero
                        cursor.execute(
                            'UPDATE beneficio_subpartida SET partida_id = ? WHERE partida_id = ?',
                            [temp_id, old_id]
                        )
                        # Actualizar partida
                        cursor.execute(
                            'UPDATE beneficio_partida SET id = ? WHERE id = ?',
                            [temp_id, old_id]
                        )

                # Ahora asignamos los IDs finales
                self.stdout.write('🔧 Paso 2: Asignando IDs finales...')
                with connection.cursor() as cursor:
                    for old_id, new_id in id_mapping.items():
                        temp_id = -old_id
                        # Actualizar partida al ID final
                        cursor.execute(
                            'UPDATE beneficio_partida SET id = ? WHERE id = ?',
                            [new_id, temp_id]
                        )
                        # Actualizar subpartidas al ID final
                        cursor.execute(
                            'UPDATE beneficio_subpartida SET partida_id = ? WHERE partida_id = ?',
                            [new_id, temp_id]
                        )

                # Resetear la secuencia de SQLite
                self.stdout.write('🔧 Paso 3: Reseteando secuencia de autoincremento...')
                max_id = len(partidas)
                with connection.cursor() as cursor:
                    cursor.execute(
                        'UPDATE sqlite_sequence SET seq = ? WHERE name = ?',
                        [max_id, 'beneficio_partida']
                    )

                self.stdout.write(self.style.SUCCESS(f'\n✅ Reset completado exitosamente!'))
                self.stdout.write(f'   - {len(partidas)} partidas renumeradas')
                self.stdout.write(f'   - Secuencia reiniciada a {max_id}')
                self.stdout.write(f'   - La próxima partida tendrá ID {max_id + 1}\n')

                # Mostrar resultado
                self.stdout.write('\nNuevo estado de las partidas:')
                self.stdout.write('-' * 50)
                for p in Partida.objects.all().order_by('id'):
                    subpartidas_count = p.subpartidas.count()
                    self.stdout.write(f'  ID: {p.id:3} | {p.numero_partida} | {p.nombre} | SubPartidas: {subpartidas_count}')
                self.stdout.write('-' * 50)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}'))
            self.stdout.write('   La operación ha sido revertida (rollback).')
            raise
