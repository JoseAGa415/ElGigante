from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Elimina subpartidas huerfanas y de partidas inactivas, y borra las partidas inactivas'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:

            # 1. Subpartidas cuya partida no existe en la tabla
            cursor.execute("""
                SELECT COUNT(*) FROM subpartidas s
                WHERE NOT EXISTS (SELECT 1 FROM partidas p WHERE p.id = s.partida_id)
            """)
            total_huerfanas = cursor.fetchone()[0]

            # 2. Subpartidas de partidas inactivas (activo = false)
            cursor.execute("""
                SELECT COUNT(*) FROM subpartidas s
                INNER JOIN partidas p ON p.id = s.partida_id
                WHERE p.activo = false
            """)
            total_inactivas = cursor.fetchone()[0]

            total = total_huerfanas + total_inactivas
            self.stdout.write(f'Subpartidas huerfanas (sin partida): {total_huerfanas}')
            self.stdout.write(f'Subpartidas de partidas inactivas: {total_inactivas}')

            if total > 0:
                # Mostrar cuales
                cursor.execute("""
                    SELECT s.id, s.numero_subpartida, s.partida_id, 'sin_partida' as motivo
                    FROM subpartidas s
                    WHERE NOT EXISTS (SELECT 1 FROM partidas p WHERE p.id = s.partida_id)
                    UNION ALL
                    SELECT s.id, s.numero_subpartida, s.partida_id, 'partida_inactiva' as motivo
                    FROM subpartidas s
                    INNER JOIN partidas p ON p.id = s.partida_id
                    WHERE p.activo = false
                """)
                for row in cursor.fetchall():
                    self.stdout.write(f'  ID:{row[0]} | {row[1]} | partida_id:{row[2]} | {row[3]}')

                # Eliminar subpartidas huerfanas
                cursor.execute("""
                    DELETE FROM subpartidas s
                    WHERE NOT EXISTS (SELECT 1 FROM partidas p WHERE p.id = s.partida_id)
                """)

                # Eliminar subpartidas de partidas inactivas
                cursor.execute("""
                    DELETE FROM subpartidas s
                    USING partidas p
                    WHERE p.id = s.partida_id AND p.activo = false
                """)

                # Eliminar partidas inactivas
                cursor.execute("DELETE FROM partidas WHERE activo = false")

                self.stdout.write(self.style.SUCCESS(
                    f'{total} subpartidas eliminadas y partidas inactivas borradas.'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('No hay nada que limpiar.'))
