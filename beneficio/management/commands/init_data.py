from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from beneficio.models import TipoCafe, Bodega

class Command(BaseCommand):
    help = 'Inicializa los datos básicos del sistema'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando datos del sistema...')
        
        # Crear superusuario si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@beneficio.com',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS('✓ Superusuario creado: admin / admin123'))
        
        # Crear tipos de café
        tipos_cafe = [
            ('Arábica Lavado', 'Café arábica procesado por método lavado'),
            ('Arábica Natural', 'Café arábica procesado por método natural'),
            ('Robusta', 'Café robusta de alta calidad'),
            ('Bourbon', 'Variedad Bourbon de especialidad'),
            ('Caturra', 'Variedad Caturra de altura'),
            ('Catuai', 'Variedad Catuai resistente'),
            ('Geisha', 'Variedad Geisha premium'),
        ]
        
        for nombre, descripcion in tipos_cafe:
            TipoCafe.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion}
            )
        self.stdout.write(self.style.SUCCESS(f'✓ {len(tipos_cafe)} tipos de café creados'))
        
        # Crear bodegas
        bodegas_data = [
            ('A', 50000, 'Zona Norte - Entrada principal'),
            ('B', 45000, 'Zona Este - Área de procesamiento'),
            ('C', 40000, 'Zona Sur - Área de almacenamiento temporal'),
            ('D', 35000, 'Zona Oeste - Área de exportación'),
        ]
        
        admin_user = User.objects.get(username='admin')
        
        for codigo, capacidad, ubicacion in bodegas_data:
            Bodega.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'capacidad_kg': capacidad,
                    'ubicacion': ubicacion,
                    'responsable': admin_user
                }
            )
        self.stdout.write(self.style.SUCCESS('✓ 4 bodegas creadas'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sistema inicializado correctamente!'))
        self.stdout.write(self.style.WARNING('\n⚠️  Recuerda cambiar la contraseña del admin en producción'))