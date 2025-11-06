from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum

# MODELOS BÁSICOS DEL SISTEMA

class TipoCafe(models.Model):
    """Modelo para los tipos de café"""
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tipo de Café"
        verbose_name_plural = "Tipos de Café"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre

class Bodega(models.Model):
    """Modelo para las bodegas A, B, C, D"""
    OPCIONES_BODEGA = [
        ('A', 'Bodega A'),
        ('B', 'Bodega B'),
        ('C', 'Bodega C'),
        ('D', 'Bodega D'),
    ]
    
    codigo = models.CharField(max_length=1, choices=OPCIONES_BODEGA, unique=True)
    capacidad_kg = models.DecimalField(max_digits=10, decimal_places=2)
    ubicacion = models.CharField(max_length=200)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bodegas')
    
    class Meta:
        ordering = ['codigo']
    
    def __str__(self):
        return f"Bodega {self.codigo}"
    
    def espacio_disponible(self):
        """Calcula el espacio disponible en la bodega"""
        ocupado = sum(lote.peso_kg for lote in self.lotes.filter(activo=True))
        return float(self.capacidad_kg) - ocupado

class Lote(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_proceso', 'En Proceso'),
        ('procesado', 'Procesado'),
        ('agotado', 'Agotado'),
    ]
    """Modelo principal para los lotes de café"""
    codigo = models.CharField(max_length=50, unique=True)
    tipo_cafe = models.CharField(max_length=100)
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='lotes')
    peso_kg = models.DecimalField(max_digits=10, decimal_places=2)
    humedad = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_ingreso = models.DateTimeField()
    proveedor = models.CharField(max_length=200)
    precio_quintal = models.DecimalField(max_digits=10, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_ingreso']
        
    def __str__(self):
        return f"Lote {self.codigo} - {self.tipo_cafe}"
    
    def etiquetas_completas(self):
        """Retorna todas las etiquetas del lote según sus procesos"""
        etiquetas = [f"Lote: {self.codigo}"]
        
        for proceso in self.procesos.all():
            etiquetas.append(f"Trilla No.{proceso.numero_trilla} - {proceso.fecha.strftime('%d/%m/%Y')}")
            for reproceso in proceso.reprocesos.all():
                etiquetas.append(f"Reproceso {reproceso.numero} de Trilla {proceso.numero_trilla}")
        
        for detalle in self.detalles_mezcla.all():
            etiquetas.append(f"Mezcla No.{detalle.mezcla.numero} - {detalle.mezcla.fecha.strftime('%d/%m/%Y')}")
        
        return etiquetas

class Procesado(models.Model):
    """Modelo para el proceso de trilla"""
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='procesos')
    numero_trilla = models.CharField(max_length=50)
    fecha = models.DateTimeField(default=timezone.now)
    
    # Pesos con unidades
    peso_inicial_kg = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_peso_inicial = models.CharField(max_length=20, default='kg')
    peso_final_kg = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_peso_final = models.CharField(max_length=20, default='kg')
    
    # Clasificación de café
    cafe_primera = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unidad_cafe_primera = models.CharField(max_length=20, default='kg')
    cafe_segunda = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unidad_cafe_segunda = models.CharField(max_length=20, default='kg')
    
    # Mermas
    catadura = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rechazo_electronica = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bajo_zaranda = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    barridos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    observaciones = models.TextField(blank=True, null=True)
    operador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Procesado"
        verbose_name_plural = "Procesados"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Trilla {self.numero_trilla} - Lote {self.lote.codigo}"
    
    @property
    def rendimiento(self):
        if self.peso_inicial_kg > 0:
            return (float(self.peso_final_kg) / float(self.peso_inicial_kg) * 100)
        return 0
    
    @property
    def merma_total(self):
        return float(self.catadura) + float(self.rechazo_electronica) + float(self.bajo_zaranda) + float(self.barridos)

class Reproceso(models.Model):
    """Modelo para reprocesos"""
    procesado = models.ForeignKey(Procesado, on_delete=models.CASCADE, related_name='reprocesos')
    numero = models.PositiveIntegerField()
    nombre = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateTimeField(default=timezone.now)
    
    peso_inicial_kg = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_peso_inicial = models.CharField(max_length=20, default='kg')
    peso_final_kg = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_peso_final = models.CharField(max_length=20, default='kg')
    
    cafe_primera = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unidad_cafe_primera = models.CharField(max_length=20, default='kg')
    cafe_segunda = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unidad_cafe_segunda = models.CharField(max_length=20, default='kg')
    
    catadura = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rechazo_electronica = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bajo_zaranda = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    barridos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    motivo = models.TextField()
    operador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Reproceso {self.numero} - Trilla {self.procesado.numero_trilla}"
    
    @property
    def rendimiento(self):
        if self.peso_inicial_kg > 0:
            return (float(self.peso_final_kg) / float(self.peso_inicial_kg) * 100)
        return 0

class Mezcla(models.Model):
    """Modelo para las mezclas de lotes procesados"""
    numero = models.PositiveIntegerField(unique=True)
    fecha = models.DateTimeField(default=timezone.now)
    peso_total_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descripcion = models.TextField()
    destino = models.CharField(max_length=200)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='mezclas_responsables')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        
    def __str__(self):
        return f"Mezcla No.{self.numero} - {self.fecha.strftime('%d/%m/%Y')}"
    
    def calcular_peso_total(self):
        return sum(float(detalle.peso_kg) for detalle in self.detalles.all())

class DetalleMezcla(models.Model):
    """Modelo para el detalle de cada mezcla"""
    mezcla = models.ForeignKey(Mezcla, on_delete=models.CASCADE, related_name='detalles')
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='detalles_mezcla')
    peso_kg = models.DecimalField(max_digits=10, decimal_places=2)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    
    class Meta:
        unique_together = ['mezcla', 'lote']
        
    def __str__(self):
        return f"Lote {self.lote.codigo} en Mezcla {self.mezcla.numero}"

class Catacion(models.Model):
    """Modelo para evaluación de catación según estándares SCA 2025"""
    TIPO_MUESTRA = [
        ('lote', 'Lote'),
        ('procesado', 'Procesado/Trilla'),
        ('reproceso', 'Reproceso'),
        ('mezcla', 'Mezcla'),
    ]
    
    TIPO_TUESTE = [
        ('claro', 'Claro (Agtron 65-75)'),
        ('medio', 'Medio (Agtron 55-65)'),
        ('oscuro', 'Oscuro (Agtron 45-55)'),
    ]
    
    tipo_muestra = models.CharField(max_length=20, choices=TIPO_MUESTRA)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, null=True, blank=True, related_name='cataciones')
    procesado = models.ForeignKey(Procesado, on_delete=models.CASCADE, null=True, blank=True, related_name='cataciones')
    reproceso = models.ForeignKey(Reproceso, on_delete=models.CASCADE, null=True, blank=True, related_name='cataciones')
    mezcla = models.ForeignKey(Mezcla, on_delete=models.CASCADE, null=True, blank=True, related_name='cataciones')
    
    codigo_muestra = models.CharField(max_length=50, unique=True)
    fecha_catacion = models.DateTimeField(default=timezone.now)
    catador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cataciones_realizadas')
    
    peso_muestra_g = models.DecimalField(max_digits=5, decimal_places=2, default=8.25)
    temperatura_agua = models.DecimalField(max_digits=4, decimal_places=1, default=93.0)
    tiempo_infusion = models.IntegerField(default=4)
    tipo_tueste = models.CharField(max_length=20, choices=TIPO_TUESTE, default='medio')
    humedad_grano = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    fragancia_aroma = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    sabor = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    sabor_residual = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    acidez = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    cuerpo = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    uniformidad = models.DecimalField(max_digits=4, decimal_places=2, default=10)
    balance = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    taza_limpia = models.DecimalField(max_digits=4, decimal_places=2, default=10)
    dulzor = models.DecimalField(max_digits=4, decimal_places=2, default=10)
    puntaje_catador = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    puntaje_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    notas_positivas = models.TextField(blank=True)
    notas_negativas = models.TextField(blank=True)
    comentarios = models.TextField(blank=True)
    clasificacion = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        ordering = ['-fecha_catacion']
        verbose_name = "Catación"
        verbose_name_plural = "Cataciones"
    
    def save(self, *args, **kwargs):
        total = 0
        if self.fragancia_aroma:
            total += float(self.fragancia_aroma)
        if self.sabor:
            total += float(self.sabor)
        if self.sabor_residual:
            total += float(self.sabor_residual)
        if self.acidez:
            total += float(self.acidez)
        if self.cuerpo:
            total += float(self.cuerpo)
        total += float(self.uniformidad or 0)
        if self.balance:
            total += float(self.balance)
        total += float(self.taza_limpia or 0)
        total += float(self.dulzor or 0)
        if self.puntaje_catador:
            total += float(self.puntaje_catador)
        
        self.puntaje_total = total
        
        if self.puntaje_total >= 90:
            self.clasificacion = "Excepcional - Specialty 90+"
        elif self.puntaje_total >= 85:
            self.clasificacion = "Excelente - Specialty 85-89"
        elif self.puntaje_total >= 80:
            self.clasificacion = "Muy Bueno - Specialty 80-84"
        elif self.puntaje_total >= 75:
            self.clasificacion = "Bueno - Premium 75-79"
        else:
            self.clasificacion = "Comercial"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Catación {self.codigo_muestra} - {self.puntaje_total} pts"

class DefectoCatacion(models.Model):
    """Modelo para registro de defectos según SCA"""
    CATEGORIA_DEFECTO = [
        ('primario', 'Defecto Primario'),
        ('secundario', 'Defecto Secundario'),
    ]
    
    catacion = models.ForeignKey(Catacion, on_delete=models.CASCADE, related_name='defectos')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_DEFECTO)
    tipo_defecto = models.CharField(max_length=50)
    cantidad = models.IntegerField(default=0)
    equivalente_defectos = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['categoria', 'tipo_defecto']
    
    def __str__(self):
        return f"{self.tipo_defecto}: {self.cantidad}"