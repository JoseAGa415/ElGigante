from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Limpia subpartidas con prefijo incorrecto, inactivas, huerfanas o de partidas inactivas'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:

            # 1. Subpartidas cuyo prefijo no coincide con el numero_partida actual
            cursor.execute("""
                SELECT s.id, s.numero_subpartida, s.partida_id, p.numero_partida
                FROM subpartidas s
                INNER JOIN partidas p ON p.id = s.partida_id
                WHERE s.numero_subpartida NOT LIKE p.numero_partida || '-%'
            """)
            prefijo_malo = cursor.fetchall()
            self.stdout.write(f'Subpartidas con prefijo incorrecto: {len(prefijo_malo)}')
            for row in prefijo_malo:
                self.stdout.write(f'  ID:{row[0]} | {row[1]} | partida_id:{row[2]} | partida actual:{row[3]}')

            # Corregir prefijo (renombrar PAR-0005-001 -> PAR-0004-001)
            for row in prefijo_malo:
                sub_id, viejo_num, partida_id, nuevo_prefijo = row
                sufijo = viejo_num.split('-')[-1]  # ej: "001"
                nuevo_numero = f"{nuevo_prefijo}-{sufijo}"
                cursor.execute(
                    "UPDATE subpartidas SET numero_subpartida = %s WHERE id = %s",
                    [nuevo_numero, sub_id]
                )
                self.stdout.write(f'  Corregido: {viejo_num} -> {nuevo_numero}')

            # 2. Subpartidas inactivas (activo=false)
            cursor.execute("SELECT COUNT(*) FROM subpartidas WHERE activo = false")
            inactivas = cursor.fetchone()[0]
            self.stdout.write(f'Subpartidas inactivas: {inactivas}')
            if inactivas:
                cursor.execute("DELETE FROM subpartidas WHERE activo = false")

            # 3. Subpartidas huerfanas (sin partida)
            cursor.execute("""
                SELECT COUNT(*) FROM subpartidas
                WHERE NOT EXISTS (SELECT 1 FROM partidas p WHERE p.id = subpartidas.partida_id)
            """)
            huerfanas = cursor.fetchone()[0]
            self.stdout.write(f'Subpartidas huerfanas: {huerfanas}')
            if huerfanas:
                cursor.execute("""
                    DELETE FROM subpartidas
                    WHERE NOT EXISTS (SELECT 1 FROM partidas p WHERE p.id = subpartidas.partida_id)
                """)

            # 4. Subpartidas de partidas inactivas + borrar partidas inactivas
            cursor.execute("""
                SELECT COUNT(*) FROM subpartidas
                WHERE partida_id IN (SELECT id FROM partidas WHERE activo = false)
            """)
            de_inactivas = cursor.fetchone()[0]
            self.stdout.write(f'Subpartidas de partidas inactivas: {de_inactivas}')
            if de_inactivas:
                cursor.execute("""
                    DELETE FROM subpartidas
                    WHERE partida_id IN (SELECT id FROM partidas WHERE activo = false)
                """)
            cursor.execute("DELETE FROM partidas WHERE activo = false")

            self.stdout.write(self.style.SUCCESS('Limpieza completada.'))
