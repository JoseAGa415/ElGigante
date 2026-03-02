from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Elimina toda subpartida inactiva, huerfana o de partida inactiva'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:

            # Mostrar lo que se va a borrar
            cursor.execute("""
                SELECT id, numero_subpartida, partida_id, activo
                FROM subpartidas
                WHERE activo = false
                ORDER BY numero_subpartida
            """)
            inactivas = cursor.fetchall()
            self.stdout.write(f'Subpartidas inactivas (activo=false): {len(inactivas)}')
            for row in inactivas:
                self.stdout.write(f'  ID:{row[0]} | {row[1]} | partida_id:{row[2]}')

            cursor.execute("""
                SELECT COUNT(*) FROM subpartidas s
                WHERE NOT EXISTS (SELECT 1 FROM partidas p WHERE p.id = s.partida_id)
            """)
            huerfanas = cursor.fetchone()[0]
            self.stdout.write(f'Subpartidas huerfanas (sin partida): {huerfanas}')

            cursor.execute("""
                SELECT COUNT(*) FROM subpartidas s
                INNER JOIN partidas p ON p.id = s.partida_id
                WHERE p.activo = false
            """)
            de_inactivas = cursor.fetchone()[0]
            self.stdout.write(f'Subpartidas de partidas inactivas: {de_inactivas}')

            total = len(inactivas) + huerfanas + de_inactivas
            if total == 0:
                self.stdout.write(self.style.SUCCESS('No hay nada que limpiar.'))
                return

            # 1. Borrar subpartidas con activo=false
            cursor.execute("DELETE FROM subpartidas WHERE activo = false")

            # 2. Borrar subpartidas huerfanas (sin partida)
            cursor.execute("""
                DELETE FROM subpartidas
                WHERE NOT EXISTS (SELECT 1 FROM partidas p WHERE p.id = subpartidas.partida_id)
            """)

            # 3. Borrar subpartidas de partidas inactivas
            cursor.execute("""
                DELETE FROM subpartidas
                WHERE partida_id IN (SELECT id FROM partidas WHERE activo = false)
            """)

            # 4. Borrar partidas inactivas
            cursor.execute("DELETE FROM partidas WHERE activo = false")
            cursor.execute("""
                SELECT COUNT(*) FROM partidas WHERE activo = false
            """)

            self.stdout.write(self.style.SUCCESS(
                f'Limpieza completada: {total} subpartidas eliminadas.'
            ))
