from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Max
from decimal import Decimal

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

    nombre = models.CharField(max_length=100, default='Bodega')
    codigo = models.CharField(max_length=1, choices=OPCIONES_BODEGA, unique=True)
    capacidad_kg = models.DecimalField(max_digits=10, decimal_places=2)
    ubicacion = models.CharField(max_length=200)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bodegas')
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['codigo']

    def __str__(self):
        return f"Bodega {self.codigo} - {self.nombre}"
    
    # def espacio_disponible(self):
    #    """Calcula el espacio disponible en la bodega"""
     #   ocupado = sum(lote.peso_kg for lote in self.lotes.filter(activo=True))
     #   return float(self.capacidad_total) - float(self.capacidad_usada)

class Lote(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_proceso', 'En Proceso'),
        ('procesado', 'Procesado'),
        ('agotado', 'Agotado'),
    ]
    """Modelo principal para los lotes de café"""
    codigo = models.CharField(max_length=50, unique=True, editable=False)
    tipo_cafe = models.CharField(max_length=100)
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='lotes')
    percha = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre de la percha")
    fila = models.CharField(max_length=50, blank=True, null=True, help_text="Fila en la percha")
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
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            ultimo_lote = Lote.objects.aggregate(Max('id'))['id__max']
            siguiente_numero = (ultimo_lote or 0) + 1
            self.codigo = f"L-{siguiente_numero:04d}"
        super().save(*args, **kwargs)
        
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
    
    # MÉTODOS PARA RECIBOS (DENTRO DE LA CLASE)
    @property
    def total_recibos(self):
        """Retorna el número total de recibos asociados a este lote"""
        return self.recibos.count()
    
    @property
    def peso_total_recibido(self):
        """Retorna el peso total de todos los recibos adicionales en kg"""
        total_kg = 0
        for recibo in self.recibos.all():
            total_kg += recibo.convertir_a_kg()
        return Decimal(str(total_kg))
    
    @property
    def monto_total_invertido(self):
        """Retorna el monto total invertido en este lote (inicial + recibos)"""
        # Inversión inicial del lote
        peso_inicial_qq = Decimal(str(self.peso_kg)) / Decimal('46')
        inversion_inicial = peso_inicial_qq * self.precio_quintal
        
        # Sumar recibos adicionales
        total_recibos = self.recibos.aggregate(Sum('monto_total'))['monto_total__sum']
        total_recibos_decimal = Decimal(str(total_recibos)) if total_recibos else Decimal('0')
        
        return inversion_inicial + total_recibos_decimal
    @property
    def peso_procesado(self):
        """Calcula el peso total que se ha procesado de este lote"""
        from decimal import Decimal
        from beneficio.models import Procesado
        
        procesados = Procesado.objects.filter(lote=self)
        total_procesado = Decimal('0')
        
        for procesado in procesados:
            total_procesado += procesado.peso_inicial_kg
        
        return total_procesado
    
    @property
    def peso_disponible(self):
        """Calcula el peso disponible para procesar (puede ser negativo si hay error)"""
        return self.peso_kg - self.peso_procesado
    
    @property
    def porcentaje_procesado(self):
        """Calcula el porcentaje del lote que ya ha sido procesado (máximo 100%)"""
        if self.peso_kg <= 0:
            return 0
        
        porcentaje = (self.peso_procesado / self.peso_kg) * 100
        
        # Limitar a 100% como máximo para la visualización
        return min(porcentaje, 100)
    
    @property
    def porcentaje_procesado_real(self):
        """Calcula el porcentaje REAL procesado (puede exceder 100% si hay error)"""
        if self.peso_kg <= 0:
            return 0
        return (self.peso_procesado / self.peso_kg) * 100
    
    @property
    def tiene_sobreprocesamiento(self):
        """Detecta si se procesó más peso del que tenía el lote (error de datos)"""
        return self.peso_procesado > self.peso_kg
    
    @property
    def exceso_procesado(self):
        """Calcula cuánto peso de más se procesó (si hay error)"""
        if self.tiene_sobreprocesamiento:
            return self.peso_procesado - self.peso_kg
        return 0
    
    @property
    def esta_completamente_procesado(self):
        """Determina si el lote ya fue completamente procesado"""
        return self.peso_disponible <= 0
    
    @property
    def puede_procesarse(self):
        """Determina si el lote tiene peso disponible para procesar"""
        # No puede procesarse si está completado O si hay sobreprocesamiento
        return self.peso_disponible > 0 and self.activo and not self.tiene_sobreprocesamiento
    
    @property
    def estado_procesamiento(self):
        """Devuelve el estado del procesamiento del lote"""
        if not self.activo:
            return "INACTIVO"
        elif self.tiene_sobreprocesamiento:
            return "ERROR"  # Nuevo estado para sobreprocesamiento
        elif self.esta_completamente_procesado:
            return "COMPLETADO"
        elif self.peso_procesado > 0:
            return "EN PROCESO"
        else:
            return "PENDIENTE"
    
    @property
    def color_estado(self):
        """Devuelve el color para el badge según el estado"""
        estado = self.estado_procesamiento
        colores = {
            "COMPLETADO": "bg-green-100 text-green-800 border-green-300",
            "EN PROCESO": "bg-yellow-100 text-yellow-800 border-yellow-300",
            "PENDIENTE": "bg-blue-100 text-blue-800 border-blue-300",
            "INACTIVO": "bg-gray-100 text-gray-800 border-gray-300",
            "ERROR": "bg-red-100 text-red-800 border-red-300"  # Color rojo para errores
        }
        return colores.get(estado, "bg-gray-100 text-gray-800")

class Procesado(models.Model):
    """Modelo para el proceso de trilla"""
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='procesos')
    
    # CAMPO ÚNICO (no duplicado)
    recibo = models.ForeignKey(
        'ReciboCafe', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='procesos_realizados',
        help_text="Recibo específico del cual proviene este procesado"
    )
    finalizado = models.BooleanField(
    default=False,
    help_text='Indica si el procesado está finalizado'
)
    
    numero_trilla = models.CharField(max_length=50, editable=False)
    fecha = models.DateTimeField(default=timezone.now)

    # CAMPOS DE HORARIO
    hora_inicio = models.TimeField(null=True, blank=True, verbose_name="Hora de Inicio")
    hora_final = models.TimeField(null=True, blank=True, verbose_name="Hora Final")

    bodega_destino = models.ForeignKey(
        Bodega,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='procesados_almacenados',
        verbose_name="Bodega de Almacenamiento"
    )
    percha = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre de la percha")
    fila = models.CharField(max_length=50, blank=True, null=True, help_text="Fila en la percha")
    finalizado = models.BooleanField(
        default=False,
        help_text='Indica si el procesado ha sido completado'
    )
    
    
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
    
    def save(self, *args, **kwargs):
        # CORREGIDO: Detectar si es nuevo ANTES del super().save()
        is_new = self.pk is None
        
        # Generar número de trilla si no existe
        if not self.numero_trilla:
            ultimo_procesado = Procesado.objects.aggregate(Max('id'))['id__max']
            siguiente_numero = (ultimo_procesado or 0) + 1
            self.numero_trilla = f"T-{siguiente_numero:04d}"
        
        super().save(*args, **kwargs)
        
        # Sumar horas al control de mantenimiento
        if is_new and self.hora_inicio and self.hora_final:
            from datetime import datetime, timedelta, time
            
            # Asegurar que son objetos time, no strings
            if isinstance(self.hora_inicio, str):
                hora_inicio = datetime.strptime(self.hora_inicio, '%H:%M').time()
            else:
                hora_inicio = self.hora_inicio
            
            if isinstance(self.hora_final, str):
                hora_final = datetime.strptime(self.hora_final, '%H:%M').time()
            else:
                hora_final = self.hora_final
            
            inicio = datetime.combine(datetime.today(), hora_inicio)
            final = datetime.combine(datetime.today(), hora_final)
            
            if final < inicio:
                final += timedelta(days=1)
            
            duracion_horas = (final - inicio).seconds / 3600
            
            try:
                control = MantenimientoPlanta.get_or_create_control()
                control.agregar_horas(duracion_horas)
            except Exception as e:
                # No fallar el guardado si hay error en mantenimiento
                print(f"Error al actualizar mantenimiento: {e}")
    
    def __str__(self):
        return f"Trilla {self.numero_trilla} - Lote {self.lote.codigo}"
    @property
    def codigo(self):
        """Retorna el número de trilla como código"""
        return f"T-{self.numero_trilla}"
    
    @property
    def rendimiento(self):
        if self.peso_inicial_kg > 0:
            return (float(self.peso_final_kg) / float(self.peso_inicial_kg) * 100)
        return 0
    
    @property
    def merma_total(self):
        return float(self.catadura) + float(self.rechazo_electronica) + float(self.bajo_zaranda) + float(self.barridos)
    
    @property
    def duracion_proceso(self):
        """Calcula la duración del proceso en horas y minutos"""
        if self.hora_inicio and self.hora_final:
            from datetime import datetime, timedelta
            inicio = datetime.combine(datetime.today(), self.hora_inicio)
            final = datetime.combine(datetime.today(), self.hora_final)
            
            if final < inicio:
                final += timedelta(days=1)
            
            duracion = final - inicio
            horas = duracion.seconds // 3600
            minutos = (duracion.seconds % 3600) // 60
            return f"{horas}h {minutos}min"
        return "No registrado"
    
    # ========== PROPIEDADES PARA SACOS DE 1.52 LB (69 KG) ==========
    
    @property
    def sacos_cafe_primera(self):
        """Calcula sacos de 152 lb (69kg) para café de primera"""
        if self.cafe_primera <= 0:
            return "Sin café 1ra"
        
        peso_valor = float(self.cafe_primera)
        
        # Convertir TODO a LIBRAS primero
        if self.unidad_cafe_primera == 'kg':
            peso_lb = peso_valor / 0.453592  # kg a libras
        elif self.unidad_cafe_primera == 'qq' or self.unidad_cafe_primera == 'quintales':
            peso_lb = (peso_valor * 46) / 0.453592  # qq → kg → libras
        elif self.unidad_cafe_primera == 'lb' or self.unidad_cafe_primera == 'libras':
            peso_lb = peso_valor  # Ya está en libras
        else:
            peso_lb = peso_valor  # Por defecto asumir que está en libras
        
        # 1 saco = 152 libras
        sacos_completos = int(peso_lb // 152)
        sobrante_lb = peso_lb % 152
        
        if sacos_completos == 0:
            # Menos de 1 saco
            return f"1 saco de {sobrante_lb:.2f} lb ({sobrante_lb * 0.453592:.2f} kg)"
        elif sobrante_lb < 1:  # Despreciar sobrantes menores a 1 lb
            return f"{sacos_completos} sacos de 152 lb (69 kg)"
        else:
            # Mostrar sacos completos + sobrante
            return f"{sacos_completos} sacos de 152 lb + 1 de {sobrante_lb:.2f} lb ({sobrante_lb * 0.453592:.2f} kg)"
    
    @property
    def sacos_cafe_segunda(self):
        """Calcula sacos de 152 lb (69kg) para café de segunda"""
        if self.cafe_segunda <= 0:
            return "Sin café 2da"
        
        peso_valor = float(self.cafe_segunda)
        
        # Convertir TODO a LIBRAS primero
        if self.unidad_cafe_segunda == 'kg':
            peso_lb = peso_valor / 0.453592  # kg a libras
        elif self.unidad_cafe_segunda == 'qq' or self.unidad_cafe_segunda == 'quintales':
            peso_lb = (peso_valor * 46) / 0.453592  # qq → kg → libras
        elif self.unidad_cafe_segunda == 'lb' or self.unidad_cafe_segunda == 'libras':
            peso_lb = peso_valor  # Ya está en libras
        else:
            peso_lb = peso_valor  # Por defecto asumir que está en libras
        
        # 1 saco = 152 libras
        sacos_completos = int(peso_lb // 152)
        sobrante_lb = peso_lb % 152
        
        if sacos_completos == 0:
            # Menos de 1 saco
            return f"1 saco de {sobrante_lb:.2f} lb ({sobrante_lb * 0.453592:.2f} kg)"
        elif sobrante_lb < 1:  # Despreciar sobrantes menores a 1 lb
            return f"{sacos_completos} sacos de 152 lb (69 kg)"
        else:
            # Mostrar sacos completos + sobrante
            return f"{sacos_completos} sacos de 152 lb + 1 de {sobrante_lb:.2f} lb ({sobrante_lb * 0.453592:.2f} kg)"
        
    @property
    def esta_vendido(self):
        """Verifica si el procesado tiene ventas asociadas completadas"""
        return self.ventas.filter(estado='completada').exists()
    
    @property
    def esta_exportado(self):
        """Verifica si el procesado tiene exportaciones entregadas"""
        return self.exportaciones.filter(estado='entregada').exists()
    
    @property
    def peso_vendido_total(self):
        """Calcula el peso total vendido"""
        from django.db.models import Sum
        return self.ventas.filter(estado='completada').aggregate(
            total=Sum('peso_vendido_kg')
        )['total'] or 0
    
    @property
    def peso_exportado_total(self):
        """Calcula el peso total exportado"""
        from django.db.models import Sum
        return self.exportaciones.filter(estado='entregada').aggregate(
            total=Sum('peso_exportado_kg')
        )['total'] or 0

    @property
    def peso_disponible(self):
        """Calcula el peso disponible restando lo vendido y exportado"""
        from django.db.models import Sum
        from decimal import Decimal
        
        # Obtener peso original - ajusta 'peso_final_kg' al nombre real en tu modelo
        peso_original = getattr(self, 'peso_final_kg', None) or getattr(self, 'peso_kg', None) or Decimal('0')
        peso_original = Decimal(str(peso_original)) if peso_original else Decimal('0')
        
        # Calcular peso vendido
        peso_vendido = self.ventas.filter(estado='completada').aggregate(total=Sum('peso_vendido_kg'))['total']
        peso_vendido = Decimal(str(peso_vendido)) if peso_vendido else Decimal('0')
        
        # Calcular peso exportado
        peso_exportado = self.exportaciones.filter(estado='entregada').aggregate(total=Sum('peso_exportado_kg'))['total']
        peso_exportado = Decimal(str(peso_exportado)) if peso_exportado else Decimal('0')
        
        return max(peso_original - peso_vendido - peso_exportado, Decimal('0'))
    
    @property
    def esta_vendido(self):
        """Verifica si el procesado tiene ventas completadas"""
        return self.ventas.filter(estado='completada').exists()
    
    @property
    def esta_exportado(self):
        """Verifica si el procesado tiene exportaciones entregadas"""
        return self.exportaciones.filter(estado='entregada').exists()
    
    @property
    def peso_vendido_total(self):
        """Calcula el peso total vendido"""
        from django.db.models import Sum
        from decimal import Decimal
        total = self.ventas.filter(estado='completada').aggregate(total=Sum('peso_vendido_kg'))['total']
        return Decimal(str(total)) if total else Decimal('0')
    
    @property
    def peso_exportado_total(self):
        """Calcula el peso total exportado"""
        from django.db.models import Sum
        from decimal import Decimal
        total = self.exportaciones.filter(estado='entregada').aggregate(total=Sum('peso_exportado_kg'))['total']
        return Decimal(str(total)) if total else Decimal('0')

class Reproceso(models.Model):
    """Modelo para reprocesos"""
    procesado = models.ForeignKey(Procesado, on_delete=models.CASCADE, related_name='reprocesos')
    numero = models.PositiveIntegerField(editable=False)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateTimeField(default=timezone.now)

    # CAMPOS DE HORARIO
    hora_inicio = models.TimeField(null=True, blank=True, verbose_name="Hora de Inicio")
    hora_final = models.TimeField(null=True, blank=True, verbose_name="Hora Final")

    bodega_destino = models.ForeignKey(
        Bodega,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reprocesos_almacenados',
        verbose_name="Bodega de Almacenamiento"
    )
    percha = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre de la percha")
    fila = models.CharField(max_length=50, blank=True, null=True, help_text="Fila en la percha")

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
    
    motivo = models.TextField()
    operador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    encargado_reproceso = models.CharField(max_length=100, blank=True, null=True, help_text="Persona a cargo del reproceso en piso")
    
    class Meta:
        ordering = ['-fecha']
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.numero:  # Solo si es nuevo
            # Obtener el último número de reproceso para este procesado
            ultimo_reproceso = Reproceso.objects.filter(
                procesado=self.procesado
            ).aggregate(Max('numero'))['numero__max']
            self.numero = (ultimo_reproceso or 0) + 1

        super().save(*args, **kwargs)

        # Sumar horas al control de mantenimiento
        if is_new and self.hora_inicio and self.hora_final:
            from datetime import datetime, timedelta, time
            
            # Asegurar que son objetos time, no strings
            if isinstance(self.hora_inicio, str):
                hora_inicio = datetime.strptime(self.hora_inicio, '%H:%M').time()
            else:
                hora_inicio = self.hora_inicio
            
            if isinstance(self.hora_final, str):
                hora_final = datetime.strptime(self.hora_final, '%H:%M').time()
            else:
                hora_final = self.hora_final
            
            inicio = datetime.combine(datetime.today(), hora_inicio)
            final = datetime.combine(datetime.today(), hora_final)
            
            if final < inicio:
                final += timedelta(days=1)
            
            duracion_horas = (final - inicio).seconds / 3600
            
            try:
                control = MantenimientoPlanta.get_or_create_control()
                control.agregar_horas(duracion_horas)
            except Exception as e:
                print(f"Error al actualizar mantenimiento: {e}")
    
    def __str__(self):
        return f"Reproceso {self.numero} - Trilla {self.procesado.numero_trilla}"
    
    @property
    def rendimiento(self):
        if self.peso_inicial_kg > 0:
            return (float(self.peso_final_kg) / float(self.peso_inicial_kg) * 100)
        return 0
    
    @property
    def merma_total(self):
        return float(self.catadura) + float(self.rechazo_electronica) + float(self.bajo_zaranda) + float(self.barridos)
    
    @property
    def duracion_proceso(self):
        """Calcula la duración del reproceso en horas y minutos"""
        if self.hora_inicio and self.hora_final:
            from datetime import datetime, timedelta
            inicio = datetime.combine(datetime.today(), self.hora_inicio)
            final = datetime.combine(datetime.today(), self.hora_final)
            
            if final < inicio:
                final += timedelta(days=1)
            
            duracion = final - inicio
            horas = duracion.seconds // 3600
            minutos = (duracion.seconds % 3600) // 60
            return f"{horas}h {minutos}min"
        return "No registrado"
    
    # ========== PROPIEDADES PARA SACOS DE 1.52 LB (69 KG) ==========
    
    @property
    def sacos_cafe_primera(self):
        """Calcula sacos de 1.52 lb (69kg) para café de primera"""
        if self.cafe_primera <= 0:
            return "Sin café 1ra"
        
        # Convertir a libras
        peso_lb = float(self.cafe_primera)
        if self.unidad_cafe_primera == 'kg':
            peso_lb = peso_lb / 0.453592  # 1 kg = 2.20462 lb
        elif self.unidad_cafe_primera == 'qq':
            peso_lb = (peso_lb * 46) / 0.453592  # qq a kg a lb
        
        # 1 saco = 1.52 lb = 69 kg
        saco_lb = 1.52
        sacos_completos = int(peso_lb // saco_lb)
        sobrante_lb = peso_lb % saco_lb
        
        if sacos_completos == 0:
            # Menos de 1 saco - mostrar el sobrante en lb y kg
            kg_sobrante = sobrante_lb * 0.453592
            return f"1 saco de {sobrante_lb:.2f} lb ({kg_sobrante:.0f} kg)"
        elif sobrante_lb < 0.05:  # Despreciar sobrantes menores a 0.05 lb
            return f"{sacos_completos} sacos de 1.52 lb (69 kg)"
        else:
            # Mostrar sacos completos + sobrante
            kg_sobrante = sobrante_lb * 0.453592
            return f"{sacos_completos} sacos de 1.52 lb + 1 de {sobrante_lb:.2f} lb ({kg_sobrante:.0f} kg)"
    
    @property
    def sacos_cafe_segunda(self):
        """Calcula sacos de 1.52 lb (69kg) para café de segunda"""
        if self.cafe_segunda <= 0:
            return "Sin café 2da"
        
        # Convertir a libras
        peso_lb = float(self.cafe_segunda)
        if self.unidad_cafe_segunda == 'kg':
            peso_lb = peso_lb / 0.453592  # 1 kg = 2.20462 lb
        elif self.unidad_cafe_segunda == 'qq':
            peso_lb = (peso_lb * 46) / 0.453592  # qq a kg a lb
        
        # 1 saco = 1.52 lb = 69 kg
        saco_lb = 1.52
        sacos_completos = int(peso_lb // saco_lb)
        sobrante_lb = peso_lb % saco_lb
        
        if sacos_completos == 0:
            # Menos de 1 saco
            kg_sobrante = sobrante_lb * 0.453592
            return f"1 saco de {sobrante_lb:.2f} lb ({kg_sobrante:.0f} kg)"
        elif sobrante_lb < 0.05:
            return f"{sacos_completos} sacos de 1.52 lb (69 kg)"
        else:
            # Mostrar sacos completos + sobrante
            kg_sobrante = sobrante_lb * 0.453592
            return f"{sacos_completos} sacos de 1.52 lb + 1 de {sobrante_lb:.2f} lb ({kg_sobrante:.0f} kg)"
    @property
    def peso_procesado(self):
        """
        Calcula cuánto peso del reproceso ya se ha vuelto a procesar
        (si el reproceso se usa como entrada para otro procesado)
        """
        from decimal import Decimal

    @property
    def peso_disponible(self):
        """Peso disponible del reproceso para volver a procesar"""
        return self.peso_final_kg - self.peso_procesado
    
    @property
    def porcentaje_procesado(self):
        """Porcentaje procesado (máximo 100% para la barra)"""
        if self.peso_final_kg <= 0:
            return 0
        porcentaje = (self.peso_procesado / self.peso_final_kg) * 100
        return min(porcentaje, 100)
    
    @property
    def porcentaje_procesado_real(self):
        """Porcentaje real (puede exceder 100%)"""
        if self.peso_final_kg <= 0:
            return 0
        return (self.peso_procesado / self.peso_final_kg) * 100
    
    @property
    def tiene_sobreprocesamiento(self):
        """Detecta si se procesó más del peso disponible"""
        return self.peso_procesado > self.peso_final_kg
    
    @property
    def exceso_procesado(self):
        """Cuánto peso de más se procesó"""
        if self.tiene_sobreprocesamiento:
            return self.peso_procesado - self.peso_final_kg
        return 0
    
    @property
    def esta_completamente_procesado(self):
        """Si el reproceso ya fue completamente re-procesado"""
        return self.peso_disponible <= 0
    
    @property
    def puede_procesarse(self):
        """Si el reproceso tiene peso disponible para re-procesar"""
        return self.peso_disponible > 0 and not self.tiene_sobreprocesamiento
    
    @property
    def estado_procesamiento(self):
        """Estado del reproceso"""
        if self.tiene_sobreprocesamiento:
            return "ERROR"
        elif self.esta_completamente_procesado:
            return "COMPLETADO"
        elif self.peso_procesado > 0:
            return "EN PROCESO"
        else:
            return "PENDIENTE"
    
    @property
    def color_estado(self):
        """Color del badge de estado"""
        estado = self.estado_procesamiento
        colores = {
            "COMPLETADO": "bg-green-100 text-green-800 border-green-300",
            "EN PROCESO": "bg-yellow-100 text-yellow-800 border-yellow-300",
            "PENDIENTE": "bg-blue-100 text-blue-800 border-blue-300",
            "ERROR": "bg-red-100 text-red-800 border-red-300"
        }
        return colores.get(estado, "bg-gray-100 text-gray-800")
    
    @property
    def esta_vendido(self):
        """Verifica si el reproceso tiene ventas asociadas completadas"""
        return self.ventas.filter(estado='completada').exists()
    
    @property
    def esta_exportado(self):
        """Verifica si el reproceso tiene exportaciones entregadas"""
        return self.exportaciones.filter(estado='entregada').exists()
    
    @property
    def peso_vendido_total(self):
        """Calcula el peso total vendido"""
        from django.db.models import Sum
        return self.ventas.filter(estado='completada').aggregate(
            total=Sum('peso_vendido_kg')
        )['total'] or 0
    
    @property
    def peso_exportado_total(self):
        """Calcula el peso total exportado"""
        from django.db.models import Sum
        return self.exportaciones.filter(estado='entregada').aggregate(
            total=Sum('peso_exportado_kg')
        )['total'] or 0
        
class Mezcla(models.Model):
    """Modelo para las mezclas de lotes procesados"""
    numero = models.PositiveIntegerField(unique=True, editable=False)
    fecha = models.DateTimeField(default=timezone.now)
    peso_total_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descripcion = models.TextField()
    destino = models.CharField(max_length=200)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='mezclas_responsables')
    created_at = models.DateTimeField(auto_now_add=True)

    # NUEVOS CAMPOS DE HORARIO
    hora_inicio = models.TimeField(null=True, blank=True, verbose_name="Hora de Inicio")
    hora_final = models.TimeField(null=True, blank=True, verbose_name="Hora Final")

    bodega_destino = models.ForeignKey(
        Bodega,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mezclas_almacenadas',
        verbose_name="Bodega de Almacenamiento"
    )
    percha = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre de la percha")
    fila = models.CharField(max_length=50, blank=True, null=True, help_text="Fila en la percha")

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not self.numero:  # Solo si es nuevo
            # Obtener el último número de mezcla
            ultima_mezcla = Mezcla.objects.aggregate(Max('numero'))['numero__max']
            self.numero = (ultima_mezcla or 0) + 1

        super().save(*args, **kwargs)

        # NUEVO: Sumar horas al control de mantenimiento
        if is_new and self.hora_inicio and self.hora_final:
            from datetime import datetime, timedelta
            inicio = datetime.combine(datetime.today(), self.hora_inicio)
            final = datetime.combine(datetime.today(), self.hora_final)
            
            if final < inicio:
                final += timedelta(days=1)
            
            duracion_horas = (final - inicio).seconds / 3600
            
            # Agregar horas al control
            control = MantenimientoPlanta.get_or_create_control()
            control.agregar_horas(duracion_horas)
        
    def __str__(self):
        return f"Mezcla No.{self.numero} - {self.fecha.strftime('%d/%m/%Y')}"
    
    def calcular_peso_total(self):
        return sum(float(detalle.peso_kg) for detalle in self.detalles.all())
    
    @property
    def duracion_proceso(self):
        """Calcula la duración de la mezcla en horas y minutos"""
        if self.hora_inicio and self.hora_final:
            from datetime import datetime, timedelta
            inicio = datetime.combine(datetime.today(), self.hora_inicio)
            final = datetime.combine(datetime.today(), self.hora_final)
            
            if final < inicio:
                final += timedelta(days=1)
            
            duracion = final - inicio
            horas = duracion.seconds // 3600
            minutos = (duracion.seconds % 3600) // 60
            return f"{horas}h {minutos}min"
        return "No registrado"
    
    @property
    def esta_vendida(self):
        """Verifica si la mezcla tiene ventas asociadas completadas"""
        return self.ventas.filter(estado='completada').exists()
    
    @property
    def esta_exportada(self):
        """Verifica si la mezcla tiene exportaciones entregadas"""
        return self.exportaciones.filter(estado='entregada').exists()
    
    @property
    def peso_vendido_total(self):
        """Calcula el peso total vendido"""
        from django.db.models import Sum
        return self.ventas.filter(estado='completada').aggregate(
            total=Sum('peso_vendido_kg')
        )['total'] or 0
    
    @property
    def peso_exportado_total(self):
        """Calcula el peso total exportado"""
        from django.db.models import Sum
        return self.exportaciones.filter(estado='entregada').aggregate(
            total=Sum('peso_exportado_kg')
        )['total'] or 0

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
        ('partida', 'Partida'),
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
    partida = models.ForeignKey('Partida', on_delete=models.CASCADE, null=True, blank=True, related_name='cataciones')
    
    codigo_muestra = models.CharField(max_length=50, unique=True, editable=False)
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
    
    # ========== CAMPOS DE GRANULOMETRÍA ==========
    gran_10 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 10")
    gran_11 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 11")
    gran_12 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 12")
    gran_13 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 13")
    gran_14 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 14")
    gran_15 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 15")
    gran_16 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 16")
    gran_17 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 17")
    gran_18 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 18")
    gran_19 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 19")
    gran_20 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 20")
    gran_21 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tamaño 21")
    
    peso_muestra_granulometria = models.CharField(max_length=50, blank=True, null=True, verbose_name="Peso Muestra (g)")
    actividad_agua = models.CharField(max_length=50, blank=True, null=True, verbose_name="Actividad de Agua")
    observaciones_granulometria = models.TextField(blank=True, null=True, verbose_name="Observaciones Granulometría")
    
    # ========== COLORES DE GRANULOMETRÍA ==========
    color_azul_verde = models.BooleanField(default=False, verbose_name="Azul Verde")
    color_verde_azulado = models.BooleanField(default=False, verbose_name="Verde Azulado")
    color_verde = models.BooleanField(default=False, verbose_name="Verde")
    color_verde_amarillento = models.BooleanField(default=False, verbose_name="Verde Amarillento")
    color_amarillo_verdoso = models.BooleanField(default=False, verbose_name="Amarillo Verdoso")
    color_amarillo = models.BooleanField(default=False, verbose_name="Amarillo")
    color_cafe = models.BooleanField(default=False, verbose_name="Café")
    color_otro = models.BooleanField(default=False, verbose_name="Otro")
    
    # ========== CAMPOS DE EVALUACIÓN DESCRIPTIVA (PARTE 1) ==========
    # Intensidades
    intensidad_fragancia = models.DecimalField(max_digits=3, decimal_places=1, default=5, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="Intensidad Fragancia")
    intensidad_aroma = models.DecimalField(max_digits=3, decimal_places=1, default=5, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="Intensidad Aroma")
    intensidad_sabor = models.DecimalField(max_digits=3, decimal_places=1, default=5, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="Intensidad Sabor")
    intensidad_sabor_residual = models.DecimalField(max_digits=3, decimal_places=1, default=5, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="Intensidad Sabor Residual")
    intensidad_acidez = models.DecimalField(max_digits=3, decimal_places=1, default=5, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="Intensidad Acidez")
    intensidad_cuerpo = models.DecimalField(max_digits=3, decimal_places=1, default=5, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name="Intensidad Cuerpo")    
    
    # Atributos Fragancia/Aroma
    attr_floral = models.BooleanField(default=False, verbose_name="Floral")
    attr_afrutado = models.BooleanField(default=False, verbose_name="Afrutado")
    attr_verde_vegetal = models.BooleanField(default=False, verbose_name="Verde/Vegetal")
    attr_tostado = models.BooleanField(default=False, verbose_name="Tostado")
    attr_nueces_cacao = models.BooleanField(default=False, verbose_name="Nueces/Cacao")
    attr_dulce = models.BooleanField(default=False, verbose_name="Dulce")
    attr_especias = models.BooleanField(default=False, verbose_name="Especias")
    attr_acido_fermentado = models.BooleanField(default=False, verbose_name="Ácido/Fermentado")
    
    # Gustos Básicos
    gusto_salado = models.BooleanField(default=False, verbose_name="Salado")
    gusto_acido = models.BooleanField(default=False, verbose_name="Ácido")
    gusto_dulce = models.BooleanField(default=False, verbose_name="Dulce")
    gusto_amargo = models.BooleanField(default=False, verbose_name="Amargo")
    gusto_umami = models.BooleanField(default=False, verbose_name="Umami")
    
    # Atributos de Cuerpo
    cuerpo_aspero = models.BooleanField(default=False, verbose_name="Áspero")
    cuerpo_aceitoso = models.BooleanField(default=False, verbose_name="Aceitoso")
    cuerpo_suave = models.BooleanField(default=False, verbose_name="Suave")
    cuerpo_seca_boca = models.BooleanField(default=False, verbose_name="Seca Boca")
    cuerpo_metalico = models.BooleanField(default=False, verbose_name="Metálico")
    
    # Notas Descriptivas
    notas_fragancia_aroma = models.TextField(blank=True, null=True, verbose_name="Notas Fragancia/Aroma")
    notas_sabor = models.TextField(blank=True, null=True, verbose_name="Notas Sabor")
    notas_residual = models.TextField(blank=True, null=True, verbose_name="Notas Residual")
    notas_acidez = models.TextField(blank=True, null=True, verbose_name="Notas Acidez")
    notas_cuerpo = models.TextField(blank=True, null=True, verbose_name="Notas Cuerpo")
    
    # ========== NOTAS AFECTIVAS INDIVIDUALES ==========
    notas_fragancia = models.TextField(blank=True, null=True, verbose_name="Notas Fragancia")
    notas_aroma = models.TextField(blank=True, null=True, verbose_name="Notas Aroma")
    notas_sabor_afectivo = models.TextField(blank=True, null=True, verbose_name="Notas Sabor")
    notas_residual_afectivo = models.TextField(blank=True, null=True, verbose_name="Notas Residual")
    notas_acidez_afectivo = models.TextField(blank=True, null=True, verbose_name="Notas Acidez")
    notas_cuerpo_afectivo = models.TextField(blank=True, null=True, verbose_name="Notas Cuerpo")
    notas_balance = models.TextField(blank=True, null=True, verbose_name="Notas Balance")
    notas_general = models.TextField(blank=True, null=True, verbose_name="Notas General")
    
    # ========== EVALUACIÓN EXTRÍNSECA (PARTE 3) ==========
    notas_extrinseca = models.TextField(blank=True, null=True, verbose_name="Notas Extrínsecas")
    notas_perfil = models.TextField(blank=True, null=True, verbose_name="Notas Perfil")
    notas_catador = models.TextField(blank=True, null=True, verbose_name="Notas del Catador")
    
    # ========== INFORMACIÓN DE ORIGEN ==========
    productor = models.CharField(max_length=200, blank=True, null=True, verbose_name="Productor")
    altitud = models.CharField(max_length=50, blank=True, null=True, verbose_name="Altitud")
    region = models.CharField(max_length=200, blank=True, null=True, verbose_name="Región")
    variedad = models.CharField(max_length=200, blank=True, null=True, verbose_name="Variedad")
    proceso = models.CharField(max_length=200, blank=True, null=True, verbose_name="Proceso")
    secado = models.CharField(max_length=200, blank=True, null=True, verbose_name="Secado")
    horas_fermentacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Horas Fermentación")
    finca = models.CharField(max_length=200, blank=True, null=True, verbose_name="Finca")
    
    # ========== DEFECTOS ORIGINALES ==========
    defectos_intensidad_2 = models.IntegerField(default=0, verbose_name="Defectos Intensidad 2")
    defectos_intensidad_4 = models.IntegerField(default=0, verbose_name="Defectos Intensidad 4")
    descripcion_defectos = models.TextField(blank=True, null=True, verbose_name="Descripción de Defectos")
    
    # ========== CAMPOS DE DEFECTOS DE TAZA (PARA DASHBOARD) ==========
    defecto_mohoso = models.BooleanField(default=False, verbose_name="Defecto Mohoso")
    defecto_fenolico = models.BooleanField(default=False, verbose_name="Defecto Fenólico")
    defecto_papa = models.BooleanField(default=False, verbose_name="Defecto Papa")
    
    # ========== TAZAS NO UNIFORMES Y DEFECTUOSAS ==========
    tazas_no_uniformes = models.PositiveIntegerField(default=0, verbose_name="Tazas No Uniformes")
    tazas_defectuosas = models.PositiveIntegerField(default=0, verbose_name="Tazas Defectuosas")
    
    # ========== DEFECTOS FÍSICOS - CATEGORÍA 1 ==========
    defecto_negro_total_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Negro Total - Cuenta")
    defecto_negro_total_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Negro Total - Completo")
    
    defecto_acido_total_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ácido Total - Cuenta")
    defecto_acido_total_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ácido Total - Completo")
    
    defecto_pergamino_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Pergamino - Cuenta")
    defecto_pergamino_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Pergamino - Completo")
    
    defecto_dano_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Daño - Cuenta")
    defecto_dano_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Daño - Completo")
    
    defecto_materia_extrana_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Materia Extraña - Cuenta")
    defecto_materia_extrana_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Materia Extraña - Completo")
    
    defecto_dano_severo_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Daño Severo - Cuenta")
    defecto_dano_severo_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Daño Severo - Completo")
    
    # ========== DEFECTOS FÍSICOS - CATEGORÍA 2 ==========
    defecto_negro_parcial_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Negro Parcial - Cuenta")
    defecto_negro_parcial_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Negro Parcial - Completo")
    
    defecto_acido_parcial_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ácido Parcial - Cuenta")
    defecto_acido_parcial_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ácido Parcial - Completo")
    
    defecto_cereza_seca_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cereza Seca - Cuenta")
    defecto_cereza_seca_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cereza Seca - Completo")
    
    defecto_hongos_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Hongos - Cuenta")
    defecto_hongos_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Hongos - Completo")
    
    defecto_flotador_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Flotador - Cuenta")
    defecto_flotador_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Flotador - Completo")
    
    defecto_inmaduro_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Inmaduro/Verde - Cuenta")
    defecto_inmaduro_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Inmaduro/Verde - Completo")
    
    defecto_insectos_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Insectos - Cuenta")
    defecto_insectos_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Insectos - Completo")
    
    defecto_marchitado_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Marchitado - Cuenta")
    defecto_marchitado_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Marchitado - Completo")
    
    defecto_concha_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Concha - Cuenta")
    defecto_concha_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Concha - Completo")
    
    defecto_cascara_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cáscara - Cuenta")
    defecto_cascara_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cáscara - Completo")
    
    defecto_dano_leve_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Daño Leve - Cuenta")
    defecto_dano_leve_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Daño Leve - Completo")
    
    defecto_rotos_count = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Rotos/Astillados - Cuenta")
    defecto_rotos_full = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Rotos/Astillados - Completo")
    
    # ========== TOTALES DE DEFECTOS ==========
    total_defectos_cat1 = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Defectos Categoría 1")
    total_defectos_cat2 = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Defectos Categoría 2")
    total_green_defects = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Green Defects")
    
    @property
    def total_defectos(self):
        """Calcula el total de defectos equivalentes"""
        return (self.defectos_intensidad_2 * 2) + (self.defectos_intensidad_4 * 4)
    
    class Meta:
        ordering = ['-fecha_catacion']
        verbose_name = "Catación"
        verbose_name_plural = "Cataciones"
    
    def save(self, *args, **kwargs):
        # Generar código automático solo si es nuevo
        if not self.codigo_muestra:
            # Generar código basado en el tipo de muestra
            prefijo = {
                'lote': 'CAT-L',
                'procesado': 'CAT-P',
                'reproceso': 'CAT-R',
                'mezcla': 'CAT-M',
                'partida': 'CAT-PAR'
            }.get(self.tipo_muestra, 'CAT')
            
            # Obtener el último número de catación
            ultimo_catacion = Catacion.objects.aggregate(Max('id'))['id__max']
            siguiente_numero = (ultimo_catacion or 0) + 1
            self.codigo_muestra = f"{prefijo}-{siguiente_numero:04d}"
        
        # Calcular puntaje total
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
        
        # Clasificar según puntaje
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
    
class Comprador(models.Model):
    """Modelo para registrar comprador"""
    nombre = models.CharField(max_length=200)
    empresa = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['nombre']
        verbose_name = "Comprador"
        verbose_name_plural = "Compradores"
    
    def __str__(self):
        return self.nombre
    
    def total_compras(self):
        """Retorna el número total de compras de este comprador"""
        return self.compras.count()
    
    def monto_total_comprado(self):
        """Retorna el monto total de todas sus compras"""
        total = self.compras.aggregate(Sum('monto_total'))['monto_total__sum']
        return total or 0
    
    def cantidad_total_comprada(self):
        """Retorna la cantidad total comprada (en kg o qq)"""
        total = self.compras.aggregate(Sum('cantidad'))['cantidad__sum']
        return total or 0


class Compra(models.Model):
    """Modelo para registrar cada compra"""
    UNIDAD_CHOICES = [
        ('kg', 'Kilogramos'),
        ('qq', 'Quintales'),
        ('lb', 'Libras'),
        ('saco', 'Sacos'),
    ]
    
    ESTADO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Pago Parcial'),
        ('pagado', 'Pagado'),
    ]
    
    comprador = models.ForeignKey(Comprador, on_delete=models.CASCADE, related_name='compras')
    fecha_compra = models.DateTimeField(default=timezone.now)
    descripcion = models.TextField(blank=True, null=True)
    
    # Cantidad y precio
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=10, choices=UNIDAD_CHOICES, default='qq')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    # Información de pago
    numero_factura = models.CharField(max_length=100, blank=True, null=True)
    metodo_pago = models.CharField(max_length=100, blank=True, null=True)
    estado_pago = models.CharField(max_length=20, choices=ESTADO_PAGO_CHOICES, default='pendiente')
    comprobante = models.FileField(
        upload_to='comprobantes/%Y/%m/',
        blank=True,
        null=True,
        help_text='Comprobante de pago (foto o documento)'
    )
    
    # Relaciones opcionales con productos
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='compras')
    procesado = models.ForeignKey(Procesado, on_delete=models.SET_NULL, null=True, blank=True, related_name='compras')
    mezcla = models.ForeignKey(Mezcla, on_delete=models.SET_NULL, null=True, blank=True, related_name='compras')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_compra']
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
    
    def save(self, *args, **kwargs):
        # Calcular monto total automáticamente
        self.monto_total = float(self.cantidad) * float(self.precio_unitario)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Compra #{self.id} - {self.comprador.nombre} - Q{self.monto_total}"

class MantenimientoPlanta(models.Model):
    """Modelo para control de mantenimiento de la planta de beneficio"""
    ESTADO_CHOICES = [
        ('operativa', 'Operativa'),
        ('requiere_mantenimiento', 'Requiere Mantenimiento'),
        ('en_mantenimiento', 'En Mantenimiento'),
    ]
    
    # Control de horas
    horas_acumuladas = models.DecimalField(max_digits=6, decimal_places=2, default=0, 
                                           help_text="Horas acumuladas desde el último mantenimiento")
    limite_horas = models.DecimalField(max_digits=6, decimal_places=2, default=40,
                                       help_text="Límite de horas antes del mantenimiento")
    
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='operativa')
    
    # Historial
    ultimo_mantenimiento = models.DateTimeField(null=True, blank=True)
    proximo_mantenimiento_estimado = models.DateTimeField(null=True, blank=True)
    
    # Información adicional
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Control de Mantenimiento"
        verbose_name_plural = "Control de Mantenimiento"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Mantenimiento Planta - {self.horas_acumuladas}h / {self.limite_horas}h"
    
    @property
    def porcentaje_uso(self):
        """Calcula el porcentaje de uso respecto al límite"""
        if self.limite_horas > 0:
            return (float(self.horas_acumuladas) / float(self.limite_horas)) * 100
        return 0
    
    @property
    def horas_restantes(self):
        """Calcula las horas restantes hasta el mantenimiento"""
        return float(self.limite_horas) - float(self.horas_acumuladas)
    
    @property
    def requiere_mantenimiento(self):
        """Verifica si la planta requiere mantenimiento"""
        return self.horas_acumuladas >= self.limite_horas
    
    def agregar_horas(self, horas):
        """Agrega horas al contador y verifica si requiere mantenimiento"""
        self.horas_acumuladas += horas
        if self.horas_acumuladas >= self.limite_horas:
            self.estado = 'requiere_mantenimiento'
        self.save()
    
    def realizar_mantenimiento(self, usuario, observaciones=''):
        """Registra un mantenimiento y reinicia el contador"""
        # Crear registro de mantenimiento
        HistorialMantenimiento.objects.create(
            control_mantenimiento=self,
            horas_acumuladas=self.horas_acumuladas,
            realizado_por=usuario,
            observaciones=observaciones
        )
        
        # Reiniciar contador
        self.horas_acumuladas = 0
        self.estado = 'operativa'
        self.ultimo_mantenimiento = timezone.now()
        self.save()
    
    @classmethod
    def get_or_create_control(cls):
        """Obtiene o crea el registro único de control"""
        control, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'horas_acumuladas': 0,
                'limite_horas': 40,
                'estado': 'operativa'
            }
        )
        return control


class HistorialMantenimiento(models.Model):
    """Historial de mantenimientos realizados a la planta"""
    control_mantenimiento = models.ForeignKey(MantenimientoPlanta, on_delete=models.CASCADE, 
                                              related_name='historial')
    fecha_mantenimiento = models.DateTimeField(default=timezone.now)
    horas_acumuladas = models.DecimalField(max_digits=6, decimal_places=2,
                                           help_text="Horas acumuladas al momento del mantenimiento")
    
    # Detalles del mantenimiento
    tipo_mantenimiento = models.CharField(max_length=100, choices=[
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo'),
        ('emergencia', 'Emergencia'),
    ], default='preventivo')
    
    observaciones = models.TextField(blank=True, null=True)
    tiempo_mantenimiento_horas = models.DecimalField(max_digits=5, decimal_places=2, 
                                                      default=0, help_text="Duración del mantenimiento")
    
    # Personal
    realizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                      related_name='mantenimientos_realizados')
    
    # Costos (opcional)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_mantenimiento']
        verbose_name = "Historial de Mantenimiento"
        verbose_name_plural = "Historial de Mantenimientos"
    
    def __str__(self):
        return f"Mantenimiento - {self.fecha_mantenimiento.strftime('%d/%m/%Y')} - {self.horas_acumuladas}h"
    
class ReciboCafe(models.Model):
    """Modelo para registrar recibos individuales de café dentro de un lote"""
    
    UNIDAD_CHOICES = [
        ('kg', 'Kilogramos'),
        ('qq', 'Quintales'),
        ('lb', 'Libras'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('proceso_parcial', 'Proceso Parcial'),
        ('procesado_completo', 'Procesado Completo'),
    ]
    
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='recibos')
    numero_recibo = models.CharField(max_length=50, unique=True, editable=False)
    fecha_recibo = models.DateTimeField(default=timezone.now)
    
    # Información del recibo
    peso = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=10, choices=UNIDAD_CHOICES, default='qq')
    humedad = models.DecimalField(max_digits=5, decimal_places=2)
    proveedor = models.CharField(max_length=200)
    precio_quintal = models.DecimalField(max_digits=10, decimal_places=2)
    numero_boletas = models.IntegerField(default=0, blank=True, null=True)
    
    # Control de procesamiento
    peso_procesado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    # Cálculos automáticos
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    
    observaciones = models.TextField(blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recibos_registrados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_recibo']
        verbose_name = "Recibo de Café"
        verbose_name_plural = "Recibos de Café"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Generar número de recibo automáticamente
        if not self.numero_recibo:
            ultimo_recibo = ReciboCafe.objects.aggregate(models.Max('id'))['id__max']
            siguiente_numero = (ultimo_recibo or 0) + 1
            self.numero_recibo = f"REC-{siguiente_numero:05d}"  # Formato: REC-00001
        
        # Calcular monto total
        peso_qq = self.convertir_a_quintales()
        self.monto_total = Decimal(str(peso_qq)) * self.precio_quintal
        
        # Actualizar estado según peso procesado
        if self.peso_procesado >= self.peso:
            self.estado = 'procesado_completo'
        elif self.peso_procesado > 0:
            self.estado = 'proceso_parcial'
        else:
            self.estado = 'pendiente'
        
        super().save(*args, **kwargs)
        
        # Si es nuevo, actualizar el peso del lote
        if is_new:
            peso_kg = self.convertir_a_kg()
            self.lote.peso_kg = Decimal(str(self.lote.peso_kg)) + Decimal(str(peso_kg))
            self.lote.save(update_fields=['peso_kg'])
    
    def delete(self, *args, **kwargs):
        # Al eliminar, restar el peso del lote
        peso_kg = self.convertir_a_kg()
        self.lote.peso_kg = Decimal(str(self.lote.peso_kg)) - Decimal(str(peso_kg))
        self.lote.save(update_fields=['peso_kg'])
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_recibo} - Lote {self.lote.codigo}"
    
    def convertir_a_kg(self):
        """Convierte el peso a kilogramos"""
        if self.unidad == 'kg':
            return float(self.peso)
        elif self.unidad == 'qq':
            return float(self.peso) * 46  # 1 quintal = 46 kg
        elif self.unidad == 'lb':
            return float(self.peso) * 0.453592  # 1 libra = 0.453592 kg
        return 0
    
    def convertir_a_quintales(self):
        """Convierte el peso a quintales"""
        peso_kg = self.convertir_a_kg()
        return peso_kg / 46
    
    @property
    def peso_disponible(self):
        """Retorna el peso disponible para procesar"""
        return float(self.peso) - float(self.peso_procesado)
    
    @property
    def porcentaje_procesado(self):
        """Retorna el porcentaje procesado"""
        if self.peso > 0:
            return (float(self.peso_procesado) / float(self.peso)) * 100
        return 0
    
    def registrar_procesamiento(self, cantidad):
        """Registra una cantidad procesada del recibo"""
        self.peso_procesado = Decimal(str(self.peso_procesado)) + Decimal(str(cantidad))
        self.save()


# Agregar estas propiedades al modelo Lote existente
# (agrégalas dentro de la clase Lote en tu models.py)

# En la clase Lote, agrega estos métodos:

    @property
    def total_recibos(self):
        """Retorna el número total de recibos"""
        return self.recibos.count()
    
    @property
    def peso_total_recibido(self):
        """Retorna el peso total de todos los recibos en kg"""
        total = 0
        for recibo in self.recibos.all():
            total += recibo.convertir_a_kg()
        return total
    
    @property
    def monto_total_invertido(self):
        """Retorna el monto total invertido en todos los recibos"""
        return self.recibos.aggregate(models.Sum('monto_total'))['monto_total__sum'] or 0

class Venta(models.Model):
    """Modelo para registrar ventas de café procesado, reprocesado o mezclas"""
    
    TIPO_PRODUCTO = [
        ('procesado', 'Procesado/Trilla'),
        ('reproceso', 'Reproceso'),
        ('mezcla', 'Mezcla'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    # ✅ NUEVO: Unidades de medida soportadas
    UNIDAD_CHOICES = [
        ('kg', 'Kilogramos'),
        ('gramos', 'Gramos'),
        ('libras', 'Libras'),
        ('quintales', 'Quintales'),
        ('bolsas', 'Bolsas'),
        ('sacos', 'Sacos'),
    ]
    
    # Identificación
    codigo_venta = models.CharField(max_length=50, unique=True, editable=False)
    fecha_venta = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    # Producto vendido (solo uno de estos será usado)
    tipo_producto = models.CharField(max_length=20, choices=TIPO_PRODUCTO)
    procesado = models.ForeignKey('Procesado', on_delete=models.CASCADE, null=True, blank=True, related_name='ventas')
    reproceso = models.ForeignKey('Reproceso', on_delete=models.CASCADE, null=True, blank=True, related_name='ventas')
    mezcla = models.ForeignKey('Mezcla', on_delete=models.CASCADE, null=True, blank=True, related_name='ventas')
    
    # ✅ NUEVO: Información de la unidad original
    unidad_medida = models.CharField(
        max_length=20, 
        choices=UNIDAD_CHOICES,
        default='kg',
        help_text="Unidad en la que se realizó la venta"
    )
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Cantidad vendida en la unidad seleccionada"
    )
    peso_por_unidad = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Solo para bolsas: peso por bolsa en libras"
    )
    
    # Información de venta (peso_vendido_kg se calcula automáticamente)
    comprador = models.ForeignKey('Comprador', on_delete=models.SET_NULL, null=True, related_name='ventas')
    peso_vendido_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=4,  # ✅ CAMBIADO: de 2 a 4 decimales para más precisión
        help_text="Peso total vendido en kilogramos (calculado automáticamente)"
    )
    precio_quintal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio por Quintal (Q)")
    precio_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    # Documentación
    numero_factura = models.CharField(max_length=100, blank=True, null=True)
    numero_contrato = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    
    # Logística
    fecha_entrega = models.DateField(null=True, blank=True)
    transportista = models.CharField(max_length=200, blank=True, null=True)
    numero_placa = models.CharField(max_length=50, blank=True, null=True)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ventas_creadas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_venta']
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
    
    def save(self, *args, **kwargs):
        # Generar código automático
        if not self.codigo_venta:
            ultimo = Venta.objects.aggregate(Max('id'))['id__max']
            siguiente = (ultimo or 0) + 1
            self.codigo_venta = f"VEN-{siguiente:05d}"
        
        # Calcular precio total (peso en kg / 45.36 para quintales * precio)
        quintales = Decimal(str(self.peso_vendido_kg)) / Decimal('45.36')
        self.precio_total = quintales * self.precio_quintal
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.codigo_venta} - {self.comprador.nombre if self.comprador else 'Sin comprador'}"
    
    @property
    def quintales_vendidos(self):
        """Calcula los quintales vendidos"""
        return float(self.peso_vendido_kg) / 45.36
    
    @property
    def producto_descripcion(self):
        """Retorna la descripción del producto vendido"""
        if self.tipo_producto == 'procesado' and self.procesado:
            return f"Procesado {self.procesado.codigo}"
        elif self.tipo_producto == 'reproceso' and self.reproceso:
            return f"Reproceso {self.reproceso.id}"
        elif self.tipo_producto == 'mezcla' and self.mezcla:
            return f"Mezcla {self.mezcla.codigo}"
        return "Producto no especificado"
    
    # ✅ NUEVO: Métodos de utilidad para mostrar información
    def get_descripcion_venta(self):
        """Retorna una descripción legible de la venta"""
        if self.unidad_medida == 'bolsas' and self.peso_por_unidad:
            return f"{self.cantidad} bolsas de {self.peso_por_unidad} lb c/u = {self.peso_vendido_kg} kg"
        else:
            return f"{self.cantidad} {self.get_unidad_medida_display()} = {self.peso_vendido_kg} kg"
    
    def cantidad_en_libras(self):
        """Convierte el peso vendido a libras"""
        return self.peso_vendido_kg / Decimal('0.453592')
    
    def cantidad_en_gramos(self):
        """Convierte el peso vendido a gramos"""
        return self.peso_vendido_kg * 1000
    
class Exportacion(models.Model):
    """Modelo para registrar exportaciones de café"""
    
    TIPO_PRODUCTO = [
        ('procesado', 'Procesado/Trilla'),
        ('reproceso', 'Reproceso'),
        ('mezcla', 'Mezcla'),
    ]
    
    ESTADO_CHOICES = [
        ('preparacion', 'En Preparación'),
        ('documentacion', 'Documentación en Proceso'),
        ('transito', 'En Tránsito'),
        ('entregada', 'Entregada'),
        ('cancelada', 'Cancelada'),
    ]
    
    TIPO_ENVIO = [
        ('maritimo', 'Marítimo'),
        ('aereo', 'Aéreo'),
        ('terrestre', 'Terrestre'),
    ]

    UNIDAD_CHOICES = [
        ('kg', 'Kilogramos'),
        ('gramos', 'Gramos'),
        ('libras', 'Libras'),
        ('quintales', 'Quintales'),
        ('bolsas', 'Bolsas'),
        ('sacos', 'Sacos'),
    ]
    
    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDAD_CHOICES,
        default='kg'
    )
    
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0
    )
    
    peso_por_unidad = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    # Identificación
    codigo_exportacion = models.CharField(max_length=50, unique=True, editable=False)
    fecha_exportacion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='preparacion')
    
    # Producto exportado
    tipo_producto = models.CharField(max_length=20, choices=TIPO_PRODUCTO)
    procesado = models.ForeignKey('Procesado', on_delete=models.CASCADE, null=True, blank=True, related_name='exportaciones')
    reproceso = models.ForeignKey('Reproceso', on_delete=models.CASCADE, null=True, blank=True, related_name='exportaciones')
    mezcla = models.ForeignKey('Mezcla', on_delete=models.CASCADE, null=True, blank=True, related_name='exportaciones')
    
    # Información de exportación
    comprador = models.ForeignKey('Comprador', on_delete=models.SET_NULL, null=True, related_name='exportaciones')
    pais_destino = models.CharField(max_length=100)
    ciudad_destino = models.CharField(max_length=100, blank=True, null=True)
    
    peso_exportado_kg = models.DecimalField(max_digits=10, decimal_places=2)
    precio_quintal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio por Quintal (Q)")
    precio_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    # Documentación aduanal
    numero_contenedor = models.CharField(max_length=100, blank=True, null=True)
    numero_bl = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bill of Lading")
    numero_factura = models.CharField(max_length=100, blank=True, null=True)
    certificado_origen = models.CharField(max_length=100, blank=True, null=True)
    
    # Logística
    tipo_envio = models.CharField(max_length=20, choices=TIPO_ENVIO, default='maritimo')
    naviera_transportista = models.CharField(max_length=200, blank=True, null=True)
    fecha_embarque = models.DateField(null=True, blank=True)
    fecha_arribo_estimada = models.DateField(null=True, blank=True)
    puerto_embarque = models.CharField(max_length=200, blank=True, null=True)
    puerto_destino = models.CharField(max_length=200, blank=True, null=True)
    
    observaciones = models.TextField(blank=True, null=True)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='exportaciones_creadas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_exportacion']
        verbose_name = "Exportación"
        verbose_name_plural = "Exportaciones"
    
    def save(self, *args, **kwargs):
        # Generar código automático
        if not self.codigo_exportacion:
            ultimo = Exportacion.objects.aggregate(Max('id'))['id__max']
            siguiente = (ultimo or 0) + 1
            self.codigo_exportacion = f"EXP-{siguiente:05d}"
        
        # Calcular precio total
        quintales = Decimal(str(self.peso_exportado_kg)) / Decimal('45.36')
        self.precio_total = Decimal(quintales) * self.precio_quintal
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.codigo_exportacion} - {self.pais_destino}"
    
    @property
    def quintales_exportados(self):
        """Calcula los quintales exportados"""
        return float(self.peso_exportado_kg) / 45.36
    
    @property
    def producto_descripcion(self):
        """Retorna la descripción del producto exportado"""
        if self.tipo_producto == 'procesado' and self.procesado:
            return f"Procesado {self.procesado.codigo}"
        elif self.tipo_producto == 'reproceso' and self.reproceso:
            return f"Reproceso {self.reproceso.id}"
        elif self.tipo_producto == 'mezcla' and self.mezcla:
            return f"Mezcla {self.mezcla.codigo}"
        return "Producto no especificado"
    
class Partida(models.Model):
    """Partida Principal - Contenedor de sub-partidas"""
    
    numero_partida = models.CharField(max_length=50, unique=True, editable=False)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    
    # UBICACIÓN FÍSICA ⭐
    bodega = models.ForeignKey('Bodega', on_delete=models.SET_NULL, null=True, blank=True, related_name='partidas_ubicadas')
    percha = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre de la percha")
    
    peso_total_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    numero_subpartidas = models.IntegerField(default=0, editable=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='partidas_creadas')
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'partidas'
        verbose_name = 'Partida'
        verbose_name_plural = 'Partidas'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        ubicacion = f" ({self.bodega.nombre} - {self.percha})" if self.bodega and self.percha else ""
        return f"{self.numero_partida} - {self.nombre}{ubicacion}"
    
    def save(self, *args, **kwargs):
        if not self.numero_partida:
            ultimo = Partida.objects.filter(
                numero_partida__startswith='PAR-'
            ).order_by('-numero_partida').first()
            
            if ultimo:
                try:
                    ultimo_num = int(ultimo.numero_partida.split('-')[1])
                    nuevo_num = ultimo_num + 1
                except:
                    nuevo_num = 1
            else:
                nuevo_num = 1
            
            self.numero_partida = f"PAR-{nuevo_num:04d}"
        
        super().save(*args, **kwargs)
    
    def actualizar_totales(self):
        from django.db.models import Sum, Count
        
        stats = self.subpartidas.filter(activo=True).aggregate(
            total_peso=Sum('peso_neto_kg'),
            total_subpartidas=Count('id')
        )
        
        self.peso_total_kg = stats['total_peso'] or 0
        self.numero_subpartidas = stats['total_subpartidas'] or 0
        self.save()
    
    @property
    def peso_en_quintales(self):
        return float(self.peso_total_kg) / 46
    
    @property
    def peso_en_libras(self):
        return float(self.peso_total_kg) * 2.20462
    
    @property
    def ubicacion_completa(self):
        """Retorna la ubicación completa formateada"""
        if self.bodega and self.percha:
            return f"{self.bodega.nombre} → {self.percha}"
        elif self.bodega:
            return f"{self.bodega.nombre}"
        return "Sin ubicación"



class SubPartida(models.Model):
    """Sub-Partida - Entrada individual dentro de una partida (Lote de Punto)"""

    # Opciones para tipo de proceso
    TIPO_PROCESO_CHOICES = [
        ('LAVADO', 'Lavado'),
        ('NATURAL', 'Natural'),
        ('HONEY', 'Honey'),
        ('LADADO', 'Ladado'),
        ('LAVADO 2 LATAS', 'Lavado 2 Latas'),
    ]

    # Opciones para calidad de taza
    TAZA_CHOICES = [
        ('SANA LIMPIA', 'Sana Limpia'),
        ('LIMPIA', 'Limpia'),
        ('REGULAR', 'Regular'),
        ('DEFECTUOSA', 'Defectuosa'),
    ]

    # Opciones para estado de inventario
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('PARCIAL', 'Parcialmente Procesado'),
        ('PROCESADO', 'Completamente Procesado'),
        ('AGOTADO', 'Agotado'),
    ]

    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='subpartidas')
    numero_subpartida = models.CharField(max_length=50, unique=True, editable=False)
    nombre = models.CharField(max_length=200, help_text="ID del lote (Ej: DELFINA / NANDO 3RAS)")

    # UBICACIÓN FÍSICA ⭐
    fila = models.CharField(max_length=50, blank=True, null=True, help_text="Fila en la percha")

    # Información del café
    tipo_proceso = models.CharField(max_length=20, choices=TIPO_PROCESO_CHOICES, default='LAVADO', help_text="Tipo de proceso del café")
    fecha_ingreso = models.DateField(blank=True, null=True, help_text="Fecha del lote")

    # Pesos y cantidades
    numero_sacos = models.IntegerField(default=1, help_text="Número de sacos")
    quintales = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cantidad en quintales (qq)")
    peso_bruto_kg = models.DecimalField(max_digits=10, decimal_places=2)
    tara_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_neto_kg = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    unidad_medida = models.CharField(max_length=10, default='kg')
    humedad = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Porcentaje de humedad")

    # Análisis de calidad (del Excel: b/15, DEFECTOS, RB, RN, SCORD)
    rendimiento_b15 = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Rendimiento b/15")
    defectos = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Porcentaje de defectos")
    rb = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True, help_text="RB")
    rn = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True, help_text="RN")
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Puntaje de catación (SCORD)")

    # Calidad de taza
    taza = models.CharField(max_length=20, choices=TAZA_CHOICES, blank=True, null=True, help_text="Calidad de taza")
    cualidades = models.TextField(blank=True, null=True, help_text="Cualidades del café (sabores, aromas)")

    # Campos adicionales de catación/análisis
    oro_sucio = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Oro sucio (peso)")
    oro_limpio = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Oro limpio (peso)")
    peso_cp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Peso C/P")
    perfil_sensorial = models.TextField(blank=True, null=True, help_text="Perfil sensorial del café")
    granulometria = models.CharField(max_length=100, blank=True, null=True, help_text="Granulometría")
    defectos_fisicos = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Defectos físicos (%)")
    defectos_verdes = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Defectos verdes (%)")
    bz_gramos = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="B/Z en gramos")
    bz_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="B/Z en porcentaje")

    # Otros campos
    proveedor = models.CharField(max_length=200, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='DISPONIBLE', help_text="Estado de inventario")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='subpartidas_creadas')
    
    class Meta:
        db_table = 'subpartidas'
        verbose_name = 'Sub-Partida'
        verbose_name_plural = 'Sub-Partidas'
        ordering = ['numero_subpartida']
    
    def __str__(self):
        ubicacion = f" - Fila {self.fila}" if self.fila else ""
        return f"{self.numero_subpartida} - {self.nombre}{ubicacion}"
    
    def save(self, *args, **kwargs):
        # Calcular peso neto
        self.peso_neto_kg = self.peso_bruto_kg - self.tara_kg
        
        # Auto-generar número
        if not self.numero_subpartida:
            partida_num = self.partida.numero_partida
            ultimo = SubPartida.objects.filter(
                partida=self.partida,
                numero_subpartida__startswith=f"{partida_num}-"
            ).order_by('-numero_subpartida').first()
            
            if ultimo:
                try:
                    ultimo_num = int(ultimo.numero_subpartida.split('-')[-1])
                    nuevo_num = ultimo_num + 1
                except:
                    nuevo_num = 1
            else:
                nuevo_num = 1
            
            self.numero_subpartida = f"{partida_num}-{nuevo_num:03d}"
        
        super().save(*args, **kwargs)
        
        # Actualizar totales de la partida
        self.partida.actualizar_totales()
    
    def delete(self, *args, **kwargs):
        partida = self.partida
        super().delete(*args, **kwargs)
        partida.actualizar_totales()
    
    @staticmethod
    def convertir_a_kg(valor, unidad):
        from decimal import Decimal
        valor = Decimal(str(valor))
        
        if unidad == 'qq':
            return valor * 46
        elif unidad == 'lb':
            return valor * Decimal('0.453592')
        else:
            return valor
    
    @property
    def peso_en_quintales(self):
        return float(self.peso_neto_kg) / 46
    
    @property
    def peso_en_libras(self):
        return float(self.peso_neto_kg) * 2.20462
    
    @property
    def porcentaje_tara(self):
        if self.peso_bruto_kg > 0:
            return float((self.tara_kg / self.peso_bruto_kg) * 100)
        return 0
    
    @property
    def ubicacion_completa(self):
        """Retorna la ubicación completa incluyendo la de la partida"""
        base = self.partida.ubicacion_completa
        if self.fila:
            return f"{base} → Fila {self.fila}"
        return base

    # ==========================================
    # PROPIEDADES DE TRAZABILIDAD DE INVENTARIO
    # ==========================================

    @property
    def quintales_procesados(self):
        """Suma de todos los movimientos de salida"""
        from django.db.models import Sum
        total = self.movimientos.aggregate(total=Sum('quintales_movidos'))['total']
        return total or Decimal('0')

    @property
    def quintales_disponibles(self):
        """Quintales restantes disponibles para procesar"""
        return self.quintales - self.quintales_procesados

    @property
    def porcentaje_procesado(self):
        """Porcentaje del lote que ha sido procesado"""
        if self.quintales > 0:
            return float((self.quintales_procesados / self.quintales) * 100)
        return 0

    def actualizar_estado(self):
        """Actualiza el estado según la disponibilidad"""
        disponibles = self.quintales_disponibles
        if disponibles <= 0:
            self.estado = 'AGOTADO'
        elif disponibles < self.quintales:
            self.estado = 'PARCIAL'
        else:
            self.estado = 'DISPONIBLE'
        self.save(update_fields=['estado'])

# ==========================================
# SEÑALES PARA MANTENER SINCRONIZACIÓN
# ==========================================
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=SubPartida)
def actualizar_partida_on_save(sender, instance, **kwargs):
    """Actualizar totales cuando se guarda una sub-partida"""
    if instance.partida:
        instance.partida.actualizar_totales()

@receiver(post_delete, sender=SubPartida)
def actualizar_partida_on_delete(sender, instance, **kwargs):
    """Actualizar totales cuando se elimina una sub-partida"""
    if instance.partida:
        instance.partida.actualizar_totales()


# =====================================================================
# MODELO: MOVIMIENTO DE SUBPARTIDA (Trazabilidad de Inventario)
# =====================================================================

class MovimientoSubPartida(models.Model):
    """Registra cada salida de peso desde una SubPartida hacia otro proceso"""

    TIPO_DESTINO_CHOICES = [
        ('PROCESADO', 'Procesado/Trilla'),
        ('REPROCESO', 'Reproceso'),
        ('MEZCLA', 'Mezcla'),
        ('VENTA', 'Venta Directa'),
        ('AJUSTE', 'Ajuste de Inventario'),
    ]

    subpartida = models.ForeignKey(
        SubPartida,
        on_delete=models.CASCADE,
        related_name='movimientos',
        help_text="SubPartida de origen"
    )
    tipo_destino = models.CharField(
        max_length=20,
        choices=TIPO_DESTINO_CHOICES,
        help_text="Tipo de proceso destino"
    )

    # Referencias opcionales al destino (se llenan según tipo_destino)
    procesado = models.ForeignKey(
        'Procesado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_subpartida',
        help_text="Procesado/Trilla destino"
    )
    reproceso = models.ForeignKey(
        'Reproceso',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_subpartida',
        help_text="Reproceso destino"
    )
    mezcla = models.ForeignKey(
        'Mezcla',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_subpartida',
        help_text="Mezcla destino"
    )

    # Cantidad movida
    quintales_movidos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cantidad en quintales (qq) movidos"
    )

    # Metadata
    fecha = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='movimientos_creados'
    )

    class Meta:
        db_table = 'movimientos_subpartida'
        verbose_name = 'Movimiento de SubPartida'
        verbose_name_plural = 'Movimientos de SubPartidas'
        ordering = ['-fecha']

    def __str__(self):
        destino = self.get_destino_display()
        return f"{self.subpartida.numero_subpartida} → {self.quintales_movidos} qq → {destino}"

    def get_destino_display(self):
        """Retorna el destino formateado con referencia"""
        if self.tipo_destino == 'PROCESADO' and self.procesado:
            return f"Trilla {self.procesado.numero_trilla}"
        elif self.tipo_destino == 'REPROCESO' and self.reproceso:
            return f"Reproceso {self.reproceso.numero}"
        elif self.tipo_destino == 'MEZCLA' and self.mezcla:
            return f"Mezcla {self.mezcla.numero}"
        return self.get_tipo_destino_display()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar estado de la subpartida
        self.subpartida.actualizar_estado()

    def delete(self, *args, **kwargs):
        subpartida = self.subpartida
        super().delete(*args, **kwargs)
        # Actualizar estado de la subpartida
        subpartida.actualizar_estado()


# =====================================================================
# MÓDULO: BENEFICIADO FINCA (Control de Corte de Café)
# =====================================================================

class Trabajador(models.Model):
    """Modelo para los trabajadores de la finca"""
    nombre_completo = models.CharField(max_length=200, verbose_name="Nombre Completo")
    cedula = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cédula")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Trabajador"
        verbose_name_plural = "Trabajadores"
        ordering = ['nombre_completo']

    def __str__(self):
        return self.nombre_completo


class PlanillaSemanal(models.Model):
    """Planilla semanal de control de corte de café"""
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio de Semana")
    fecha_fin = models.DateField(verbose_name="Fecha Fin de Semana")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='planillas_creadas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Planilla Semanal"
        verbose_name_plural = "Planillas Semanales"
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"Planilla {self.fecha_inicio.strftime('%d/%m/%Y')} - {self.fecha_fin.strftime('%d/%m/%Y')}"

    def total_libras_semana(self):
        """Calcula el total de libras cortadas en la semana"""
        return self.registros_diarios.aggregate(
            total=Sum('libras_cortadas')
        )['total'] or Decimal('0.00')

    def total_quintales_semana(self):
        """Calcula el total en quintales (qq) de la semana"""
        return self.total_libras_semana() / Decimal('100.00')


class RegistroDiario(models.Model):
    """Registro diario de corte por trabajador"""
    DIAS_SEMANA = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
    ]

    planilla = models.ForeignKey(
        PlanillaSemanal,
        on_delete=models.CASCADE,
        related_name='registros_diarios',
        verbose_name="Planilla"
    )
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.CASCADE,
        related_name='registros',
        verbose_name="Trabajador"
    )
    dia_semana = models.CharField(
        max_length=10,
        choices=DIAS_SEMANA,
        verbose_name="Día"
    )
    fecha = models.DateField(verbose_name="Fecha")

    # Libras cortadas
    libras_cortadas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Libras Cortadas"
    )

    # Tipo de café (puede seleccionar de la lista o escribir manualmente)
    tipo_cafe = models.ForeignKey(
        TipoCafe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_corte',
        verbose_name="Tipo de Café (Lista)"
    )
    tipo_cafe_manual = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Tipo de Café (Manual)",
        help_text="Si el tipo de café no está en la lista, escríbelo aquí"
    )

    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro Diario"
        verbose_name_plural = "Registros Diarios"
        ordering = ['fecha', 'trabajador']
        unique_together = ['planilla', 'trabajador', 'dia_semana', 'fecha']

    def __str__(self):
        return f"{self.trabajador.nombre_completo} - {self.get_dia_semana_display()} ({self.libras_cortadas} lb)"

    def get_tipo_cafe_display_full(self):
        """Retorna el tipo de café, ya sea de la lista o manual"""
        if self.tipo_cafe:
            return self.tipo_cafe.nombre
        elif self.tipo_cafe_manual:
            return self.tipo_cafe_manual
        return "No especificado"

    def quintales(self):
        """Convierte libras a quintales"""
        return self.libras_cortadas / Decimal('100.00')