from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Elimina subpartidas huerfanas (sin partida activa asociada)'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Contar subpartidas huerfanas
            cursor.execute("""
                SELECT COUNT(*) FROM subpartidas s
                WHERE NOT EXISTS (
                    SELECT 1 FROM partidas p WHERE p.id = s.partida_id
                )
            """)
            total = cursor.fetchone()[0]
            self.stdout.write(f'Subpartidas huerfanas encontradas: {total}')

            if total == 0:
                self.stdout.write(self.style.SUCCESS('No hay nada que limpiar.'))
                return

            # Mostrar cuales son
            cursor.execute("""
                SELECT s.id, s.numero_subpartida, s.partida_id
                FROM subpartidas s
                WHERE NOT EXISTS (
                    SELECT 1 FROM partidas p WHERE p.id = s.partida_id
                )
            """)
            for row in cursor.fetchall():
                self.stdout.write(f'  ID:{row[0]} | {row[1]} | partida_id:{row[2]}')

            # Eliminarlas
            cursor.execute("""
                DELETE FROM subpartidas s
                WHERE NOT EXISTS (
                    SELECT 1 FROM partidas p WHERE p.id = s.partida_id
                )
            """)
            self.stdout.write(self.style.SUCCESS(f'{total} subpartidas huerfanas eliminadas.'))
