from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import ExtractYear
from django.core.paginator import Paginator
from collections import OrderedDict
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import ExtractYear, ExtractMonth, TruncDate
import calendar

from .models import (
    Lote, Procesado, Reproceso, Mezcla, DetalleMezcla,
    Bodega, TipoCafe, Catacion, DefectoCatacion
)

# ==========================================
# VISTAS DE AUTENTICACIÓN
# ==========================================

def login_view(request):
    """Vista de inicio de sesión"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenido {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'beneficio/login.html')


def logout_view(request):
    """Vista de cierre de sesión"""
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('login')


# ==========================================
# VISTA PRINCIPAL - DASHBOARD
# ==========================================

@login_required
def dashboard(request):
    """Vista principal del dashboard"""
    total_lotes = Lote.objects.filter(activo=True).count()
    total_procesados = Procesado.objects.count()
    total_reprocesos = Reproceso.objects.count()
    total_mezclas = Mezcla.objects.count()
    
    # Obtener información de bodegas
    bodegas = Bodega.objects.all()
    bodegas_data = []
    for bodega in bodegas:
        ocupado = Lote.objects.filter(bodega=bodega, activo=True).aggregate(
            total=Sum('peso_kg')
        )['total'] or 0
        
        disponible = float(bodega.capacidad_kg) - float(ocupado)
        porcentaje_ocupado = (float(ocupado) / float(bodega.capacidad_kg) * 100) if bodega.capacidad_kg > 0 else 0
        
        bodegas_data.append({
            'codigo': bodega.codigo,
            'capacidad': bodega.capacidad_kg,
            'ocupado': ocupado,
            'disponible': disponible,
            'porcentaje': porcentaje_ocupado
        })
    
    # Últimos lotes ingresados
    ultimos_lotes = Lote.objects.filter(activo=True).order_by('-fecha_ingreso')[:5]
    today = timezone.now().date()
    
    # --- Gráfico por Mes (Últimos 12 meses) ---
    twelve_months_ago = today - timedelta(days=365)
    
    procesado_por_mes = Procesado.objects.filter(
        fecha__gte=twelve_months_ago
    ).annotate(
        year=ExtractYear('fecha'),
        month=ExtractMonth('fecha')
    ).values(
        'year', 'month'
    ).annotate(
        total=Sum('peso_inicial_kg') # Sumamos el peso inicial
    ).order_by(
        'year', 'month'
    )
    
    labels_por_mes = []
    data_por_mes = []
    month_names = list(calendar.month_abbr) # Nombres de mes (Ene, Feb, etc.)
    
    for item in procesado_por_mes:
        labels_por_mes.append(f"{month_names[item['month']]}-{item['year']}")
        data_por_mes.append(float(item['total'])) # Convertir Decimal a float

    # --- Gráfico por Día (Últimos 30 días) ---
    thirty_days_ago = today - timedelta(days=30)
    
    procesado_por_dia = Procesado.objects.filter(
        fecha__date__gte=thirty_days_ago
    ).annotate(
        dia=TruncDate('fecha') # Agrupar por día
    ).values(
        'dia'
    ).annotate(
        total=Sum('peso_inicial_kg')
    ).order_by(
        'dia'
    )
    
    # Crear un diccionario para rellenar días sin datos
    dias_en_rango = { (thirty_days_ago + timedelta(days=i)): 0 for i in range(31) }
    
    # Llenar el diccionario con los datos de la consulta
    for item in procesado_por_dia:
        if item['dia'] in dias_en_rango:
            dias_en_rango[item['dia']] = float(item['total'])
            
    # Crear las listas finales para el gráfico
    labels_por_dia = [dia.strftime('%d-%b') for dia in dias_en_rango.keys()]
    data_por_dia = list(dias_en_rango.values())
    
    context = {
        'total_lotes': total_lotes,
        'total_procesados': total_procesados,
        'total_reprocesos': total_reprocesos,
        'total_mezclas': total_mezclas,
        'bodegas': bodegas_data,
        'ultimos_lotes': ultimos_lotes,
    }
    return render(request, 'beneficio/dashboard.html', context)


# ==========================================
# VISTA DE HISTORIAL
# ==========================================

@login_required
def historial(request):
    """Vista de historial de todas las operaciones"""
    # Obtener el tipo de historial solicitado (por defecto: procesado)
    tipo_historial = request.GET.get('tipo', 'procesado')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    items = []
    
    if tipo_historial == 'procesado':
        items = Procesado.objects.all().order_by('-fecha')
        
        if fecha_inicio:
            items = items.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            items = items.filter(fecha__date__lte=fecha_fin)
            
    elif tipo_historial == 'reproceso':
        items = Reproceso.objects.all().order_by('-fecha')
        
        if fecha_inicio:
            items = items.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            items = items.filter(fecha__date__lte=fecha_fin)
            
    elif tipo_historial == 'mezclas':
        items = Mezcla.objects.all().order_by('-fecha')
        
        if fecha_inicio:
            items = items.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            items = items.filter(fecha__date__lte=fecha_fin)
    
    elif tipo_historial == 'catacion':
        items = Catacion.objects.select_related('lote', 'procesado', 'reproceso', 'mezcla', 'catador').all()
        fecha_field = 'fecha_catacion' # Usamos el campo correcto para Catacion
    
    if fecha_inicio:
        items = items.filter(**{f'{fecha_field}__date__gte': fecha_inicio})
    if fecha_fin:
        items = items.filter(**{f'{fecha_field}__date__lte': fecha_fin})

    context = {
        'tipo_historial': tipo_historial,
        'items': items,
        # Pasamos request.GET al contexto para mantener los filtros en el formulario
        'request': request,
    }
    # Asegúrate que la ruta del template sea correcta si has movido archivos
    return render(request, 'beneficio/historial/index.html', context)


# ==========================================
# VISTAS DE LOTES
# ==========================================

@login_required
def lista_lotes(request):
    """Lista todos los lotes"""
    codigo = request.GET.get('codigo')
    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')
    
    lotes = Lote.objects.all().order_by('-fecha_ingreso')
    
    if codigo:
        lotes = lotes.filter(codigo__icontains=codigo)
    
    if tipo:
        lotes = lotes.filter(tipo_cafe__icontains=tipo)
    
    if estado:
        if estado == 'activo':
            lotes = lotes.filter(activo=True)
        else:
            lotes = lotes.filter(activo=False)
    
    context = {
        'lotes': lotes,
    }
    return render(request, 'beneficio/lotes/lista.html', context)


@login_required
def crear_lote(request):
    """Crear nuevo lote"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lote = Lote()
                lote.codigo = request.POST.get('codigo')
                lote.tipo_cafe = request.POST.get('tipo_cafe')
                lote.bodega_id = request.POST.get('bodega_id')
                lote.peso_kg = request.POST.get('peso_kg')
                lote.humedad = request.POST.get('humedad')
                lote.fecha_ingreso = request.POST.get('fecha_ingreso')
                lote.proveedor = request.POST.get('proveedor')
                lote.precio_quintal = request.POST.get('precio_quintal')
                lote.observaciones = request.POST.get('observaciones', '')
                lote.created_by = request.user
                lote.save()
                
                messages.success(request, f'Lote {lote.codigo} creado exitosamente')
                return redirect('lista_lotes')
        except Exception as e:
            messages.error(request, f'Error al crear lote: {str(e)}')
    
    context = {
        'bodegas': Bodega.objects.all(),  # Esta línea ya existe y está correcta
    }
    return render(request, 'beneficio/lotes/crear.html', context)

@login_required
def detalle_lote(request, pk):
    """Ver detalle de un lote"""
    lote = get_object_or_404(Lote, pk=pk)
    
    context = {
        'lote': lote,
    }
    return render(request, 'beneficio/lotes/detalle.html', context)


@login_required
def editar_lote(request, pk):
    """Editar un lote"""
    lote = get_object_or_404(Lote, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lote.codigo = request.POST.get('codigo')
                lote.tipo_cafe = request.POST.get('tipo_cafe')
                lote.bodega_id = request.POST.get('bodega_id')
                lote.peso_kg = request.POST.get('peso_kg')
                lote.humedad = request.POST.get('humedad')
                lote.fecha_ingreso = request.POST.get('fecha_ingreso')
                lote.proveedor = request.POST.get('proveedor')
                lote.precio_quintal = request.POST.get('precio_quintal')
                lote.observaciones = request.POST.get('observaciones', '')
                lote.save()
                
                messages.success(request, f'Lote {lote.codigo} actualizado exitosamente')
                return redirect('detalle_lote', pk=lote.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar lote: {str(e)}')
    
    context = {
        'lote': lote,
        'bodegas': Bodega.objects.all(),
    }
    return render(request, 'beneficio/lotes/editar.html', context)



@login_required
def eliminar_lote(request, pk):
    """Eliminar un lote"""
    lote = get_object_or_404(Lote, pk=pk)
    
    if request.method == 'POST':
        codigo = lote.codigo
        lote.activo = False
        lote.save()
        messages.success(request, f'Lote {codigo} eliminado exitosamente')
        return redirect('lista_lotes')
    
    context = {
        'lote': lote,
    }
    return render(request, 'beneficio/lotes/eliminar.html', context)


# ==========================================
# VISTAS DE PROCESADOS
# ==========================================

@login_required
def lista_procesados(request):
    # Obtener filtros
    fecha = request.GET.get('fecha')
    lote_codigo = request.GET.get('lote')
    year_filter = request.GET.get('year')
    
    # Filtrar procesados
    procesados = Procesado.objects.select_related('lote', 'lote__bodega', 'operador').all()
    
    if fecha:
        procesados = procesados.filter(fecha__date=fecha)
    
    if lote_codigo:
        procesados = procesados.filter(lote__codigo__icontains=lote_codigo)
    
    if year_filter:
        procesados = procesados.filter(fecha__year=year_filter)
    
    # Ordenar por fecha descendente
    procesados = procesados.order_by('-fecha')
    
    # Agrupar por año
    procesados_por_year = OrderedDict()
    for procesado in procesados:
        year = procesado.fecha.year
        if year not in procesados_por_year:
            procesados_por_year[year] = []
        procesados_por_year[year].append(procesado)
    
    # Obtener lista de años disponibles para el filtro
    years = Procesado.objects.annotate(
        year=ExtractYear('fecha')
    ).values_list('year', flat=True).distinct().order_by('-year')
    
    context = {
        'procesados_por_year': procesados_por_year,
        'procesados': Procesado.objects.all(),  # Para compatibilidad
        'years': years,
    }
    return render(request, 'beneficio/procesados/lista.html', context)

@login_required
def crear_procesado(request, lote_id):
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            procesado = Procesado()
            procesado.lote = lote
            procesado.numero_trilla = request.POST.get('numero_trilla')
            procesado.encargado_trilla = request.POST.get('encargado_trilla')
            procesado.personas_trabajando = request.POST.get('personas_trabajando')
            procesado.estado = request.POST.get('estado', 'en_proceso')  
            procesado.peso_inicial_kg = request.POST.get('peso_inicial_kg')
            procesado.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
            procesado.peso_final_kg = request.POST.get('peso_final_kg')
            procesado.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
            procesado.cafe_primera = request.POST.get('cafe_primera', 0)
            procesado.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
            procesado.cafe_segunda = request.POST.get('cafe_segunda', 0)
            procesado.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
            procesado.catadura = request.POST.get('catadura', 0)
            procesado.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
            procesado.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
            procesado.barridos = request.POST.get('barridos', 0)
            procesado.observaciones = request.POST.get('observaciones')
            procesado.operador = request.user
            procesado.save()
            
            messages.success(request, f'Trilla #{procesado.numero_trilla} procesada exitosamente')
            return redirect('detalle_procesado', pk=procesado.id)
    
    context = {'lote': lote}
    return render(request, 'beneficio/procesados/crear.html', context)

@login_required
def detalle_procesado(request, pk):
    """Ver detalle de un procesado"""
    procesado = get_object_or_404(Procesado, pk=pk)
    
    context = {
        'procesado': procesado,
    }
    return render(request, 'beneficio/procesados/detalle.html', context)


@login_required
def editar_procesado(request, pk):
    """Editar un procesado"""
    procesado = get_object_or_404(Procesado, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                procesado.peso_inicial_kg = request.POST.get('peso_inicial_kg')
                procesado.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                procesado.peso_final_kg = request.POST.get('peso_final_kg')
                procesado.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                procesado.cafe_primera = request.POST.get('cafe_primera', 0)
                procesado.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                procesado.cafe_segunda = request.POST.get('cafe_segunda', 0)
                procesado.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                procesado.catadura = request.POST.get('catadura', 0)
                procesado.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
                procesado.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
                procesado.barridos = request.POST.get('barridos', 0)
                procesado.observaciones = request.POST.get('observaciones', '')
                procesado.save()
                
                messages.success(request, f'Procesado #{procesado.numero_trilla} actualizado exitosamente')
                return redirect('detalle_procesado', pk=procesado.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar procesado: {str(e)}')
    
    context = {
        'procesado': procesado,
    }
    return render(request, 'beneficio/procesados/editar.html', context)


@login_required
def eliminar_procesado(request, pk):
    """Eliminar un procesado"""
    procesado = get_object_or_404(Procesado, pk=pk)
    
    if request.method == 'POST':
        procesado.delete()
        messages.success(request, 'Procesado eliminado exitosamente')
        return redirect('lista_procesados')
    
    context = {
        'procesado': procesado,
    }
    return render(request, 'beneficio/procesados/eliminar.html', context)


# ==========================================
# VISTAS DE REPROCESOS
# ==========================================

@login_required
def lista_reprocesos(request):
    """Lista todos los reprocesos"""
    fecha = request.GET.get('fecha')
    procesado = request.GET.get('procesado')
    
    reprocesos = Reproceso.objects.all().order_by('-fecha')
    
    if fecha:
        reprocesos = reprocesos.filter(fecha__date=fecha)
    
    if procesado:
        reprocesos = reprocesos.filter(procesado_id=procesado)
    
    context = {
        'reprocesos': reprocesos,
        'procesados': Procesado.objects.all(),
    }
    return render(request, 'beneficio/reprocesos/lista.html', context)


@login_required
def crear_reproceso(request, procesado_id):
    """Crear reproceso desde un procesado"""
    procesado = get_object_or_404(Procesado, pk=procesado_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            ultimo_reproceso = Reproceso.objects.filter(procesado=procesado).order_by('-numero').first()
            siguiente_numero = (ultimo_reproceso.numero + 1) if ultimo_reproceso else 1
            
            reproceso = Reproceso()
            reproceso.procesado = procesado
            reproceso.numero = siguiente_numero
            reproceso.nombre = request.POST.get('nombre', '')
            reproceso.peso_inicial_kg = request.POST.get('peso_inicial_kg')
            reproceso.peso_final_kg = request.POST.get('peso_final_kg')
            reproceso.catadura = request.POST.get('catadura', 0)
            reproceso.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
            reproceso.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
            reproceso.barridos = request.POST.get('barridos', 0)
            reproceso.motivo = request.POST.get('motivo')
            reproceso.operador = request.user
            reproceso.save()
            
            messages.success(request, f'Reproceso #{reproceso.numero} creado exitosamente')
            return redirect('detalle_reproceso', pk=reproceso.id)
    
    ultimo_reproceso = Reproceso.objects.filter(procesado=procesado).order_by('-numero').first()
    siguiente_numero = (ultimo_reproceso.numero + 1) if ultimo_reproceso else 1
    
    context = {
        'procesado': procesado,
        'siguiente_numero': siguiente_numero,
    }
    return render(request, 'beneficio/reprocesos/crear.html', context)

@login_required
def detalle_reproceso(request, pk):
    """Ver detalle de un reproceso"""
    reproceso = get_object_or_404(Reproceso, pk=pk)
    
    context = {
        'reproceso': reproceso,
    }
    return render(request, 'beneficio/reprocesos/detalle.html', context)


@login_required
def editar_reproceso(request, pk):
    """Editar/renombrar un reproceso"""
    reproceso = get_object_or_404(Reproceso, pk=pk)
    
    if request.method == 'POST':
        try:
            # Solo actualizar nombre y motivo, NO los pesos
            reproceso.nombre = request.POST.get('nombre', '')
            reproceso.motivo = request.POST.get('motivo')
            reproceso.save(update_fields=['nombre', 'motivo'])  # Solo actualiza estos campos
            
            messages.success(request, f'Reproceso #{reproceso.numero} actualizado exitosamente')
            return redirect('detalle_reproceso', pk=reproceso.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    context = {
        'reproceso': reproceso,
    }
    return render(request, 'beneficio/reprocesos/editar.html', context)

@login_required
def reprocesar_reproceso(request, pk):
    """Crear un nuevo reproceso a partir de un reproceso existente"""
    reproceso_origen = get_object_or_404(Reproceso, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear nuevo reproceso
                nuevo_reproceso = Reproceso()
                nuevo_reproceso.procesado = reproceso_origen.procesado
                nuevo_reproceso.numero = reproceso_origen.procesado.reprocesos.count() + 1
                nuevo_reproceso.nombre = request.POST.get('nombre', f'Re-reproceso de #{reproceso_origen.numero}')
                nuevo_reproceso.peso_inicial_kg = request.POST.get('peso_inicial_kg')
                nuevo_reproceso.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                nuevo_reproceso.peso_final_kg = request.POST.get('peso_final_kg')
                nuevo_reproceso.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                nuevo_reproceso.cafe_primera = request.POST.get('cafe_primera', 0)
                nuevo_reproceso.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                nuevo_reproceso.cafe_segunda = request.POST.get('cafe_segunda', 0)
                nuevo_reproceso.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                nuevo_reproceso.catadura = request.POST.get('catadura', 0)
                nuevo_reproceso.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
                nuevo_reproceso.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
                nuevo_reproceso.barridos = request.POST.get('barridos', 0)
                nuevo_reproceso.motivo = request.POST.get('motivo')
                nuevo_reproceso.operador = request.user
                nuevo_reproceso.save()
                
                messages.success(request, f'Reproceso #{nuevo_reproceso.numero} creado exitosamente desde Reproceso #{reproceso_origen.numero}')
                return redirect('detalle_reproceso', pk=nuevo_reproceso.pk)
        except Exception as e:
            messages.error(request, f'Error al crear reproceso: {str(e)}')
    
    context = {
        'reproceso_origen': reproceso_origen,
    }
    return render(request, 'beneficio/reprocesos/crear_desde_reproceso.html', context)

@login_required
def eliminar_reproceso(request, pk):
    """Eliminar un reproceso"""
    reproceso = get_object_or_404(Reproceso, pk=pk)
    
    if request.method == 'POST':
        reproceso.delete()
        messages.success(request, 'Reproceso eliminado exitosamente')
        return redirect('lista_reprocesos')
    
    context = {
        'reproceso': reproceso,
    }
    return render(request, 'beneficio/reprocesos/eliminar.html', context)


# ==========================================
# VISTAS DE MEZCLAS
# ==========================================

@login_required
def lista_mezclas(request):
    """Lista todas las mezclas"""
    mezclas = Mezcla.objects.all().order_by('-fecha')
    
    context = {
        'mezclas': mezclas,
    }
    return render(request, 'beneficio/mezclas/lista.html', context)


@login_required
def crear_mezcla(request):
    """Crear nueva mezcla"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                ultima_mezcla = Mezcla.objects.all().order_by('-numero').first()
                siguiente_numero = (ultima_mezcla.numero + 1) if ultima_mezcla else 1
                
                mezcla = Mezcla()
                mezcla.numero = siguiente_numero
                mezcla.descripcion = request.POST.get('descripcion', '')
                mezcla.destino = request.POST.get('destino', '')
                mezcla.responsable = request.user
                mezcla.save()
                
                import json
                componentes = json.loads(request.POST.get('componentes', '[]'))
                
                peso_total = 0
                for comp in componentes:
                    lote_id = comp.get('lote_id')
                    peso = float(comp.get('peso', 0))
                    
                    if lote_id and peso > 0:
                        lote = Lote.objects.get(pk=lote_id)
                        peso_total += peso
                        
                        DetalleMezcla.objects.create(
                            mezcla=mezcla,
                            lote=lote,
                            peso_kg=peso,
                            porcentaje=0
                        )
                
                if peso_total > 0:
                    for detalle in mezcla.detalles.all():
                        detalle.porcentaje = (float(detalle.peso_kg) / peso_total) * 100
                        detalle.save()
                
                mezcla.peso_total_kg = peso_total
                mezcla.save()
                
                messages.success(request, f'Mezcla #{mezcla.numero} creada exitosamente')
                return redirect('detalle_mezcla', pk=mezcla.id)
                
        except Exception as e:
            messages.error(request, f'Error al crear mezcla: {str(e)}')
    
    # Obtener TODAS las opciones disponibles
    opciones_mezcla = []
    
    # 1. LOTES SIN PROCESAR
    for lote in Lote.objects.filter(activo=True):
        opciones_mezcla.append({
            'id': lote.id,
            'tipo': '📦 Lote',
            'codigo': lote.codigo,
            'descripcion': f"{lote.tipo_cafe} - Bodega {lote.bodega.codigo}",
            'peso_disponible': float(lote.peso_kg)
        })
    
    # 2. PROCESADOS (TRILLAS)
    for procesado in Procesado.objects.select_related('lote').all():
        opciones_mezcla.append({
            'id': procesado.lote.id,
            'tipo': '⚙️ Procesado',
            'codigo': f"Trilla #{procesado.numero_trilla}",
            'descripcion': f"Lote {procesado.lote.codigo} - {procesado.lote.tipo_cafe}",
            'peso_disponible': float(procesado.peso_final_kg)
        })
    
    # 3. REPROCESOS
    for reproceso in Reproceso.objects.select_related('procesado__lote').all():
        nombre = reproceso.nombre if reproceso.nombre else f"Reproceso #{reproceso.numero}"
        opciones_mezcla.append({
            'id': reproceso.procesado.lote.id,
            'tipo': '🔄 Reproceso',
            'codigo': nombre,
            'descripcion': f"Lote {reproceso.procesado.lote.codigo} - De Trilla #{reproceso.procesado.numero_trilla}",
            'peso_disponible': float(reproceso.peso_final_kg)
        })
    
    import json
    context = {
        'opciones_json': json.dumps(opciones_mezcla),
        'total_opciones': len(opciones_mezcla)
    }
    return render(request, 'beneficio/mezclas/crear.html', context)

@login_required
def detalle_mezcla(request, pk):
    """Ver detalle de una mezcla"""
    mezcla = get_object_or_404(Mezcla, pk=pk)
    detalles = mezcla.detalles.all()
    
    context = {
        'mezcla': mezcla,
        'detalles': detalles,
    }
    return render(request, 'beneficio/mezclas/detalle.html', context)


@login_required
def editar_mezcla(request, pk):
    """Editar una mezcla"""
    mezcla = get_object_or_404(Mezcla, pk=pk)
    
    if request.method == 'POST':
        messages.success(request, 'Mezcla actualizada exitosamente')
        return redirect('detalle_mezcla', pk=mezcla.pk)
    
    context = {
        'mezcla': mezcla,
        'lotes': Lote.objects.filter(activo=True),
        'procesados': Procesado.objects.all(),
    }
    return render(request, 'beneficio/mezclas/editar.html', context)


@login_required
def eliminar_mezcla(request, pk):
    """Eliminar una mezcla"""
    mezcla = get_object_or_404(Mezcla, pk=pk)
    
    if request.method == 'POST':
        numero = mezcla.numero
        mezcla.delete()
        messages.success(request, f'Mezcla #{numero} eliminada exitosamente')
        return redirect('lista_mezclas')
    
    context = {
        'mezcla': mezcla,
    }
    return render(request, 'beneficio/mezclas/eliminar.html', context)

# ==========================================
# VISTAS DE CATACIÓN
# ==========================================

from django.db.models import Sum, Avg

@login_required
def lista_procesados(request):
    """Lista todos los procesados"""
    procesados = Procesado.objects.all().order_by('-fecha')
    lotes = Lote.objects.all()

    # Filtros
    numero_trilla = request.GET.get('numero_trilla')
    lote_id = request.GET.get('lote')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if numero_trilla:
        procesados = procesados.filter(numero_trilla__icontains=numero_trilla)
    if lote_id:
        procesados = procesados.filter(lote_id=lote_id)
    if fecha_desde:
        procesados = procesados.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        procesados = procesados.filter(fecha__lte=fecha_hasta)

    # Calcular estadísticas CON LOS CAMPOS CORRECTOS
    estadisticas = procesados.aggregate(
        total_entrada=Sum('peso_inicial_kg'),  # ← CORRECTO
        total_salida=Sum('peso_final_kg'),     # ← CORRECTO
    )

    # Paginación
    paginator = Paginator(procesados, 10)
    page = request.GET.get('page')
    procesados_paginados = paginator.get_page(page)

    context = {
        'procesados': procesados_paginados,
        'lotes': lotes,
        'estadisticas': estadisticas,
    }
    return render(request, 'beneficio/procesados/lista.html', context)

import decimal # Para manejar Decimal conversion error potential

@login_required
def crear_catacion(request):
    """Vista para crear una nueva catación"""
    if request.method == 'POST':
        # --- Obtener TODOS los datos del formulario (sin eliminar nada) ---
        codigo_muestra = request.POST.get('codigo_muestra')
        tipo_muestra = request.POST.get('tipo_muestra')
        fecha_catacion_str = request.POST.get('fecha_catacion')
        humedad_grano_str = request.POST.get('humedad_grano')

        lote_id = request.POST.get('lote_id') if tipo_muestra == 'lote' else None # Usar lote_id como en el form
        procesado_id = request.POST.get('procesado_id') if tipo_muestra == 'procesado' else None # Usar procesado_id
        reproceso_id = request.POST.get('reproceso_id') if tipo_muestra == 'reproceso' else None # Usar reproceso_id
        mezcla_id = request.POST.get('mezcla_id') if tipo_muestra == 'mezcla' else None # Usar mezcla_id

        # Datos Descriptivos (Intensidades) - No están en el modelo Catacion
        intensidad_fragancia = request.POST.get('intensidad_fragancia', 5)
        intensidad_aroma = request.POST.get('intensidad_aroma', 5)
        intensidad_sabor = request.POST.get('intensidad_sabor', 5)
        intensidad_sabor_residual = request.POST.get('intensidad_sabor_residual', 5)
        intensidad_acidez = request.POST.get('intensidad_acidez', 5)
        intensidad_cuerpo = request.POST.get('intensidad_cuerpo', 5)

        # Atributos de Fragancia/Aroma (Booleanos) - No están en el modelo Catacion
        attr_floral = request.POST.get('attr_floral') == 'on'
        # ... (obtener todos los attr_... de la misma forma) ...
        attr_acido_fermentado = request.POST.get('attr_acido_fermentado') == 'on'

        # Gustos básicos (Booleanos) - No están en el modelo Catacion
        gusto_salado = request.POST.get('gusto_salado') == 'on'
        # ... (obtener todos los gusto_... de la misma forma) ...
        gusto_umami = request.POST.get('gusto_umami') == 'on'

        # Cuerpo (Booleanos) - No están en el modelo Catacion
        cuerpo_aspero = request.POST.get('cuerpo_aspero') == 'on'
        # ... (obtener todos los cuerpo_... de la misma forma) ...
        cuerpo_metalico = request.POST.get('cuerpo_metalico') == 'on'

        # Notas descriptivas - Podrían mapearse a comentarios/notas_positivas/negativas
        notas_fragancia_aroma = request.POST.get('notas_fragancia_aroma')
        notas_sabor = request.POST.get('notas_sabor')
        notas_residual = request.POST.get('notas_residual')
        notas_acidez = request.POST.get('notas_acidez')
        notas_cuerpo = request.POST.get('notas_cuerpo')
        notas_extrinseca = request.POST.get('notas_extrinseca')

        # Evaluación Afectiva - Puntajes (SÍ están en el modelo, necesitan conversión)
        fragancia_str = request.POST.get('fragancia', '0') # Se mapeará a fragancia_aroma
        aroma_str = request.POST.get('aroma', '0') # No tiene campo directo en el modelo base
        sabor_str = request.POST.get('sabor', '0')
        sabor_residual_str = request.POST.get('sabor_residual', '0')
        acidez_str = request.POST.get('acidez', '0')
        cuerpo_str = request.POST.get('cuerpo', '0')
        uniformidad_str = request.POST.get('uniformidad', '10') # Valor viene de JS
        taza_limpia_str = request.POST.get('taza_limpia', '10') # Valor viene de JS
        dulzor_str = request.POST.get('dulzor', '10') # Valor viene de JS
        balance_str = request.POST.get('balance', '0')
        general_str = request.POST.get('general', '0') # Se mapeará a puntaje_catador

        # Defectos - Necesitan ir al modelo DefectoCatacion
        defectos_intensidad_2_str = request.POST.get('defectos_intensidad_2', '0')
        defectos_intensidad_4_str = request.POST.get('defectos_intensidad_4', '0')
        total_defectos_str = request.POST.get('total_defectos', '0') # Calculado por JS
        descripcion_defectos = request.POST.get('descripcion_defectos')

        # Puntaje total - Calculado por JS, pero el modelo lo recalcula en save()
        puntaje_total_str = request.POST.get('puntaje_total', '0')

        # Información adicional - No está en el modelo Catacion
        notas_perfil = request.POST.get('notas_perfil')
        productor = request.POST.get('productor')
        altitud = request.POST.get('altitud')
        region = request.POST.get('region')
        variedad = request.POST.get('variedad')
        proceso = request.POST.get('proceso')
        secado = request.POST.get('secado')
        horas_fermentacion = request.POST.get('horas_fermentacion')
        finca = request.POST.get('finca')
        notas_catador = request.POST.get('notas_catador') # Podría mapearse a comentarios

        # --- Conversiones y Validación ---
        try:
            fecha_catacion = timezone.datetime.fromisoformat(fecha_catacion_str) if fecha_catacion_str else timezone.now()
        except (ValueError, TypeError):
             fecha_catacion = timezone.now()
             messages.warning(request, f'Formato de fecha inválido para {codigo_muestra}, usando fecha actual.')

        try:
            humedad_grano = decimal.Decimal(humedad_grano_str) if humedad_grano_str else None
        except (decimal.InvalidOperation, ValueError, TypeError):
            humedad_grano = None
            # No enviar mensaje si es opcional y está vacío
            if humedad_grano_str:
                 messages.warning(request, f'Valor de humedad inválido para {codigo_muestra}.')

        try:
            # Convertir solo los puntajes que SÍ van al modelo
            fragancia_aroma = decimal.Decimal(fragancia_str) # Mapeo fragancia -> fragancia_aroma
            sabor = decimal.Decimal(sabor_str)
            sabor_residual = decimal.Decimal(sabor_residual_str)
            acidez = decimal.Decimal(acidez_str)
            cuerpo = decimal.Decimal(cuerpo_str)
            uniformidad = decimal.Decimal(uniformidad_str)
            balance = decimal.Decimal(balance_str)
            taza_limpia = decimal.Decimal(taza_limpia_str)
            dulzor = decimal.Decimal(dulzor_str)
            puntaje_catador = decimal.Decimal(general_str) # Mapeo general -> puntaje_catador

            # Convertir defectos (aunque no vayan directo al create)
            defectos_intensidad_2 = int(defectos_intensidad_2_str)
            defectos_intensidad_4 = int(defectos_intensidad_4_str)

        except (decimal.InvalidOperation, ValueError, TypeError) as e:
            messages.error(request, f'Error al convertir valores numéricos: {e}. Revise los puntajes o defectos ingresados.')
            context = {
                'lotes': Lote.objects.all(),
                'procesados': Procesado.objects.all(),
                'mezclas': Mezcla.objects.all(),
                'reprocesos': Reproceso.objects.all(),
                'form_data': request.POST # Enviar datos POST de vuelta al template
            }
            return render(request, 'beneficio/catacion/crear.html', context)


        # --- Construir kwargs SOLO con campos del MODELO Catacion ---
        create_kwargs = {
            'codigo_muestra': codigo_muestra,
            'tipo_muestra': tipo_muestra,
            'fecha_catacion': fecha_catacion,
            'humedad_grano': humedad_grano,
            'lote_id': lote_id,
            'procesado_id': procesado_id,
            'reproceso_id': reproceso_id, # Asegúrate que el modelo tenga 'reproceso' ForeignKey
            'mezcla_id': mezcla_id,
            'catador': request.user,

            # Puntajes mapeados
            'fragancia_aroma': fragancia_aroma,
            'sabor': sabor,
            'sabor_residual': sabor_residual,
            'acidez': acidez,
            'cuerpo': cuerpo,
            'uniformidad': uniformidad,
            'balance': balance,
            'taza_limpia': taza_limpia,
            'dulzor': dulzor,
            'puntaje_catador': puntaje_catador,

            # Mapeo opcional de notas a campos existentes (ajusta según tu modelo)
            'comentarios': f"Notas Frag/Aroma: {notas_fragancia_aroma or 'N/A'}\n"
                         f"Notas Sabor: {notas_sabor or 'N/A'}\n"
                         f"Notas Residual: {notas_residual or 'N/A'}\n"
                         f"Notas Acidez: {notas_acidez or 'N/A'}\n"
                         f"Notas Cuerpo: {notas_cuerpo or 'N/A'}\n"
                         f"Notas Extrínseca: {notas_extrinseca or 'N/A'}\n"
                         f"Notas Perfil: {notas_perfil or 'N/A'}\n"
                         f"Notas Catador: {notas_catador or 'N/A'}",
            # O podrías usar notas_positivas/notas_negativas si existen
        }

        # --- Crear la catación ---
        try:
            catacion = Catacion.objects.create(**create_kwargs)

            # --- Crear DefectoCatacion relacionado (Opcional) ---
            if defectos_intensidad_2 > 0:
                DefectoCatacion.objects.create(
                    catacion=catacion,
                    categoria='secundario', # Asumiendo intensidad 2 es secundario
                    tipo_defecto='Defecto(s) Int. 2',
                    cantidad=defectos_intensidad_2,
                    equivalente_defectos=decimal.Decimal(defectos_intensidad_2 * 2) # O lógica SCA
                )
            if defectos_intensidad_4 > 0:
                 DefectoCatacion.objects.create(
                    catacion=catacion,
                    categoria='primario', # Asumiendo intensidad 4 es primario
                    tipo_defecto='Defecto(s) Int. 4',
                    cantidad=defectos_intensidad_4,
                    equivalente_defectos=decimal.Decimal(defectos_intensidad_4 * 4) # O lógica SCA
                )
            # Podrías guardar 'descripcion_defectos' en la nota del defecto o en Catacion.comentarios

            messages.success(request, f'Catación {codigo_muestra} creada exitosamente.')
            return redirect('detalle_catacion', pk=catacion.pk)

        except Exception as e:
             messages.error(request, f'Error al guardar la catación: {e}')
             # Renderizar de nuevo con datos
             context = {
                'lotes': Lote.objects.all(),
                'procesados': Procesado.objects.all(),
                'mezclas': Mezcla.objects.all(),
                'reprocesos': Reproceso.objects.all(),
                'form_data': request.POST
             }
             return render(request, 'beneficio/catacion/crear.html', context)


    # --- GET - Mostrar formulario ---
    context = {
        'lotes': Lote.objects.all(),
        'procesados': Procesado.objects.all(),
        'mezclas': Mezcla.objects.all(),
        'reprocesos': Reproceso.objects.all(), # Añadir reprocesos
    }
    # Ruta corregida
    return render(request, 'beneficio/catacion/crear.html', context)

@login_required
def eliminar_catacion(request, pk):
    """Eliminar una catación"""
    catacion = get_object_or_404(Catacion, pk=pk)
    
    if request.method == 'POST':
        catacion.delete()
        messages.success(request, 'Catación eliminada exitosamente')
        return redirect('lista_cataciones')
    
    context = {
        'catacion': catacion,
    }
    return render(request, 'beneficio/catacion/eliminar.html', context)

@login_required
def detalle_catacion(request, pk):
    """Ver detalle de una catación"""
    catacion = get_object_or_404(Catacion, pk=pk)
    
    context = {
        'catacion': catacion,
    }
    return render(request, 'beneficio/catacion/detalle.html', context)

@login_required
def editar_reproceso(request, pk):
    """Editar/renombrar un reproceso"""
    reproceso = get_object_or_404(Reproceso, pk=pk)
    
    if request.method == 'POST':
        try:
            reproceso.nombre = request.POST.get('nombre')
            reproceso.motivo = request.POST.get('motivo')
            reproceso.save()
            
            messages.success(request, f'Reproceso #{reproceso.numero} actualizado exitosamente')
            return redirect('detalle_reproceso', pk=reproceso.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    context = {
        'reproceso': reproceso,
    }
    return render(request, 'beneficio/reprocesos/editar.html', context)


@login_required
def reprocesar_reproceso(request, pk):
    """Crear un nuevo reproceso a partir de un reproceso existente"""
    reproceso_origen = get_object_or_404(Reproceso, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear nuevo reproceso
                nuevo_reproceso = Reproceso()
                nuevo_reproceso.procesado = reproceso_origen.procesado
                nuevo_reproceso.numero = reproceso_origen.procesado.reprocesos.count() + 1
                nuevo_reproceso.nombre = request.POST.get('nombre', f'Re-reproceso de #{reproceso_origen.numero}')
                nuevo_reproceso.peso_inicial_kg = request.POST.get('peso_inicial_kg')
                nuevo_reproceso.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                nuevo_reproceso.peso_final_kg = request.POST.get('peso_final_kg')
                nuevo_reproceso.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                nuevo_reproceso.cafe_primera = request.POST.get('cafe_primera', 0)
                nuevo_reproceso.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                nuevo_reproceso.cafe_segunda = request.POST.get('cafe_segunda', 0)
                nuevo_reproceso.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                nuevo_reproceso.catadura = request.POST.get('catadura', 0)
                nuevo_reproceso.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
                nuevo_reproceso.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
                nuevo_reproceso.barridos = request.POST.get('barridos', 0)
                nuevo_reproceso.motivo = request.POST.get('motivo')
                nuevo_reproceso.operador = request.user
                nuevo_reproceso.save()
                
                messages.success(request, f'Reproceso #{nuevo_reproceso.numero} creado exitosamente desde Reproceso #{reproceso_origen.numero}')
                return redirect('detalle_reproceso', pk=nuevo_reproceso.pk)
        except Exception as e:
            messages.error(request, f'Error al crear reproceso: {str(e)}')
    
    context = {
        'reproceso_origen': reproceso_origen,
    }
    return render(request, 'beneficio/reprocesos/crear_desde_reproceso.html', context)

@login_required
def continuar_procesado(request, pk):
    """Dar continuidad al procesado sin perder datos"""
    procesado = get_object_or_404(Procesado, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Actualizar todos los campos
                procesado.peso_inicial_kg = request.POST.get('peso_inicial_kg')
                procesado.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                procesado.peso_final_kg = request.POST.get('peso_final_kg')
                procesado.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                procesado.cafe_primera = request.POST.get('cafe_primera', 0)
                procesado.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                procesado.cafe_segunda = request.POST.get('cafe_segunda', 0)
                procesado.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                procesado.catadura = request.POST.get('catadura', 0)
                procesado.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
                procesado.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
                procesado.barridos = request.POST.get('barridos', 0)
                procesado.observaciones = request.POST.get('observaciones', '')
                procesado.save()
                
                messages.success(request, f'Procesado #{procesado.numero_trilla} actualizado exitosamente')
                return redirect('detalle_procesado', pk=procesado.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar procesado: {str(e)}')
    
    # IMPORTANTE: Pasar el procesado al contexto
    context = {
        'procesado': procesado,
    }
    return render(request, 'beneficio/procesados/continuar.html', context)

@login_required
def seleccionar_lote_procesar(request):
    """Vista para seleccionar el lote a procesar"""
    lotes = Lote.objects.all().select_related('bodega')
    
    context = {
        'lotes': lotes,
    }
    return render(request, 'beneficio/procesados/seleccionar_lote.html', context)

@login_required
def imprimir_catacion(request, pk):
    catacion = get_object_or_404(Catacion, pk=pk)
    context = {'catacion': catacion}
    return render(request, 'beneficio/cataciones/imprimir.html', context)

@login_required
def lista_cataciones(request):
    """Vista para listar todas las cataciones"""
    cataciones = Catacion.objects.all().select_related('lote', 'procesado', 'mezcla', 'catador').order_by('-fecha_catacion')
    
    # Filtros
    codigo = request.GET.get('codigo')
    tipo_muestra = request.GET.get('tipo_muestra')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    puntaje_min = request.GET.get('puntaje_min')
    
    if codigo:
        cataciones = cataciones.filter(codigo_muestra__icontains=codigo)
    if tipo_muestra:
        cataciones = cataciones.filter(tipo_muestra=tipo_muestra)
    if fecha_desde:
        cataciones = cataciones.filter(fecha_catacion__gte=fecha_desde)
    if fecha_hasta:
        cataciones = cataciones.filter(fecha_catacion__lte=fecha_hasta)
    if puntaje_min:
        cataciones = cataciones.filter(puntaje_total__gte=puntaje_min)

        # --- ¡CORRECCIÓN! ---
    # Añade el contexto y el return render
    context = {
        'cataciones': cataciones,
        # Puedes añadir otras variables al contexto si tu template las necesita
    }
    return render(request, 'beneficio/catacion/lista.html', context)
    # --- FIN CORRECCIÓN ---