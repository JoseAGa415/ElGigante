from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
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
from decimal import Decimal, InvalidOperation
import json
from datetime import datetime, timedelta, date
from django.db.models.functions import TruncMonth, TruncYear, TruncDate, ExtractYear, ExtractMonth
from .models import Procesado, Reproceso, Mezcla, Venta, Exportacion, Comprador

from .models import (
    Lote, Procesado, Reproceso, Mezcla, DetalleMezcla,
    Bodega, TipoCafe, Catacion, DefectoCatacion, Comprador, Compra,
    MantenimientoPlanta, HistorialMantenimiento, ReciboCafe, Partida, SubPartida,
    Trabajador, PlanillaSemanal, RegistroDiario, MovimientoSubPartida, EtiquetaLote
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
    
    # ========== TU CÓDIGO ORIGINAL (sin cambios) ==========
    total_lotes = Lote.objects.filter(activo=True).count()
    total_procesados = Procesado.objects.count()
    total_reprocesos = Reproceso.objects.count()
    total_mezclas = Mezcla.objects.count()
    total_compradores = Comprador.objects.filter(activo=True).count()
    
    # Obtener información de bodegas
    bodegas = Bodega.objects.all()
    bodegas_data = []
    for bodega in bodegas:
        ocupado = Lote.objects.filter(bodega=bodega, activo=True).aggregate(
            total=Sum('peso_kg')
        )['total'] or 0
        
        disponible = Decimal(bodega.capacidad_kg) - Decimal(ocupado)
        porcentaje_ocupado = (Decimal(ocupado) / Decimal(bodega.capacidad_kg) * 100) if bodega.capacidad_kg > 0 else 0
        
        bodegas_data.append({
            'codigo': bodega.codigo,
            'capacidad': bodega.capacidad_kg,
            'ocupado': ocupado,
            'disponible': disponible,
            'porcentaje': porcentaje_ocupado
        })
    
    # Últimos lotes ingresados
    ultimos_lotes = Lote.objects.select_related('bodega').filter(activo=True).order_by('-fecha_ingreso')[:5]
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
        total=Sum('peso_inicial_kg')
    ).order_by(
        'year', 'month'
    )
    
    labels_por_mes = []
    data_por_mes = []
    month_names = list(calendar.month_abbr)
    
    for item in procesado_por_mes:
        labels_por_mes.append(f"{month_names[item['month']]}-{item['year']}")
        data_por_mes.append(float(item['total']))

    # --- Gráfico por Día (Últimos 30 días) ---
    thirty_days_ago = today - timedelta(days=30)
    
    procesado_por_dia = Procesado.objects.filter(
        fecha__date__gte=thirty_days_ago
    ).annotate(
        dia=TruncDate('fecha') 
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
    
    # ========== NUEVO CÓDIGO DE CATACIÓN ==========
    
    # Obtener filtros
    year_filter = request.GET.get('year', datetime.now().year)
    month_filter = request.GET.get('month', None)
    
    # Obtener cataciones filtradas
    cataciones = Catacion.objects.all()
    if year_filter:
        cataciones = cataciones.filter(fecha_catacion__year=year_filter)
    if month_filter:
        cataciones = cataciones.filter(fecha_catacion__month=month_filter)
    
    # --- Datos para gráfico de defectos de taza por mes ---
    cataciones_por_mes = Catacion.objects.filter(
        fecha_catacion__year=year_filter
    ).annotate(
        mes=TruncMonth('fecha_catacion')
    ).values('mes').annotate(
        total_mohoso=Count('id', filter=Q(defecto_mohoso=True)),
        total_fenolico=Count('id', filter=Q(defecto_fenolico=True)),
        total_papa=Count('id', filter=Q(defecto_papa=True)),
    ).order_by('mes')
    
    meses_catacion = []
    mohoso_data = []
    fenolico_data = []
    papa_data = []
    
    for item in cataciones_por_mes:
        meses_catacion.append(item['mes'].strftime('%B'))
        mohoso_data.append(item['total_mohoso'])
        fenolico_data.append(item['total_fenolico'])
        papa_data.append(item['total_papa'])
    
    # --- Estadísticas de defectos físicos ---
    defectos_cat1 = cataciones.aggregate(
        negro_total=Sum('defecto_negro_total_count'),
        acido_total=Sum('defecto_acido_total_count'),
        pergamino=Sum('defecto_pergamino_count'),
        dano=Sum('defecto_dano_count'),
        materia_extrana=Sum('defecto_materia_extrana_count'),
        dano_severo=Sum('defecto_dano_severo_count'),
    )
    
    defectos_cat2 = cataciones.aggregate(
        negro_parcial=Sum('defecto_negro_parcial_count'),
        acido_parcial=Sum('defecto_acido_parcial_count'),
        cereza_seca=Sum('defecto_cereza_seca_count'),
        hongos=Sum('defecto_hongos_count'),
        flotador=Sum('defecto_flotador_count'),
        inmaduro=Sum('defecto_inmaduro_count'),
        insectos=Sum('defecto_insectos_count'),
        marchitado=Sum('defecto_marchitado_count'),
        concha=Sum('defecto_concha_count'),
        cascara=Sum('defecto_cascara_count'),
        dano_leve=Sum('defecto_dano_leve_count'),
        rotos=Sum('defecto_rotos_count'),
    )
    
    # Preparar datos para gráficos
    defectos_labels_cat1 = ['Negro Total', 'Ácido Total', 'Pergamino', 'Daño', 'Materia Extraña', 'Daño Severo']
    defectos_valores_cat1 = [
        defectos_cat1['negro_total'] or 0,
        defectos_cat1['acido_total'] or 0,
        defectos_cat1['pergamino'] or 0,
        defectos_cat1['dano'] or 0,
        defectos_cat1['materia_extrana'] or 0,
        defectos_cat1['dano_severo'] or 0,
    ]
    
    defectos_labels_cat2 = ['Negro Parcial', 'Ácido Parcial', 'Cereza Seca', 'Hongos', 'Flotador', 
                            'Inmaduro', 'Insectos', 'Marchitado', 'Concha', 'Cáscara', 'Daño Leve', 'Rotos']
    defectos_valores_cat2 = [
        defectos_cat2['negro_parcial'] or 0,
        defectos_cat2['acido_parcial'] or 0,
        defectos_cat2['cereza_seca'] or 0,
        defectos_cat2['hongos'] or 0,
        defectos_cat2['flotador'] or 0,
        defectos_cat2['inmaduro'] or 0,
        defectos_cat2['insectos'] or 0,
        defectos_cat2['marchitado'] or 0,
        defectos_cat2['concha'] or 0,
        defectos_cat2['cascara'] or 0,
        defectos_cat2['dano_leve'] or 0,
        defectos_cat2['rotos'] or 0,
    ]
    
    # --- Estadísticas generales de catación ---
    total_cataciones = cataciones.count()
    promedio_puntaje = cataciones.aggregate(Avg('puntaje_total'))['puntaje_total__avg'] or 0
    cataciones_con_defectos = cataciones.exclude(total_green_defects=0).count()
    
    # Clasificación de cafés
    cafe_excepcional = cataciones.filter(puntaje_total__gte=90).count()
    cafe_excelente = cataciones.filter(puntaje_total__gte=85, puntaje_total__lt=90).count()
    cafe_muy_bueno = cataciones.filter(puntaje_total__gte=80, puntaje_total__lt=85).count()
    cafe_bueno = cataciones.filter(puntaje_total__gte=75, puntaje_total__lt=80).count()
    cafe_comercial = cataciones.filter(puntaje_total__lt=75).count()
    
    clasificacion_labels = ['Excepcional (90+)', 'Excelente (85-89)', 'Muy Bueno (80-84)', 'Bueno (75-79)', 'Comercial (<75)']
    clasificacion_valores = [cafe_excepcional, cafe_excelente, cafe_muy_bueno, cafe_bueno, cafe_comercial]
    
    # Estadísticas de tazas
    tazas_stats = cataciones.aggregate(
        total_no_uniformes=Sum('tazas_no_uniformes'),
        total_defectuosas=Sum('tazas_defectuosas'),
        promedio_uniformidad=Avg('uniformidad'),
        promedio_taza_limpia=Avg('taza_limpia'),
    )
    
    # Años disponibles para filtro
    years = Catacion.objects.dates('fecha_catacion', 'year', order='DESC')
    
    # ========== CONTEXT COMPLETO ==========
    context = {
        # Tu data original
        'total_lotes': total_lotes,
        'total_procesados': total_procesados,
        'total_reprocesos': total_reprocesos,
        'total_mezclas': total_mezclas,
        'total_compradores': total_compradores,
        'bodegas': bodegas_data,
        'ultimos_lotes': ultimos_lotes,
        'labels_por_mes': json.dumps(labels_por_mes),
        'data_por_mes': json.dumps(data_por_mes),
        'labels_por_dia': json.dumps(labels_por_dia),
        'data_por_dia': json.dumps(data_por_dia),
        
        # Nuevos datos de catación
        'year_filter': year_filter,
        'month_filter': month_filter,
        'years': years,
        'total_cataciones': total_cataciones,
        'promedio_puntaje': round(promedio_puntaje, 2),
        'cataciones_con_defectos': cataciones_con_defectos,
        'meses_catacion': json.dumps(meses_catacion),
        'mohoso_data': json.dumps(mohoso_data),
        'fenolico_data': json.dumps(fenolico_data),
        'papa_data': json.dumps(papa_data),
        'defectos_labels_cat1': json.dumps(defectos_labels_cat1),
        'defectos_valores_cat1': json.dumps(defectos_valores_cat1),
        'defectos_labels_cat2': json.dumps(defectos_labels_cat2),
        'defectos_valores_cat2': json.dumps(defectos_valores_cat2),
        'clasificacion_labels': json.dumps(clasificacion_labels),
        'clasificacion_valores': json.dumps(clasificacion_valores),
        'total_tazas_no_uniformes': tazas_stats['total_no_uniformes'] or 0,
        'total_tazas_defectuosas': tazas_stats['total_defectuosas'] or 0,
        'promedio_uniformidad': round(tazas_stats['promedio_uniformidad'] or 0, 2),
        'promedio_taza_limpia': round(tazas_stats['promedio_taza_limpia'] or 0, 2),
    }
    
    return render(request, 'beneficio/dashboard.html', context)

# ==========================================
# VISTA DE HISTORIAL
# ==========================================

@login_required
def historial(request):
    """Vista de historial de todas las operaciones"""
    tipo_historial = request.GET.get('tipo', 'procesado')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    items = []
    
    if tipo_historial == 'procesado':
        items = Procesado.objects.select_related('lote', 'operador').all().order_by('-fecha')
        if fecha_inicio:
            items = items.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            items = items.filter(fecha__date__lte=fecha_fin)
            
    elif tipo_historial == 'reproceso':
        items = Reproceso.objects.select_related('procesado__lote', 'operador').all().order_by('-fecha')
        if fecha_inicio:
            items = items.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            items = items.filter(fecha__date__lte=fecha_fin)
            
    elif tipo_historial == 'mezclas':
        items = Mezcla.objects.select_related('responsable').all().order_by('-fecha')
        if fecha_inicio:
            items = items.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            items = items.filter(fecha__date__lte=fecha_fin)
    
    elif tipo_historial == 'catacion':
        items = Catacion.objects.select_related(
            'lote', 'procesado', 'reproceso', 'mezcla', 'catador'
        ).all().order_by('-fecha_catacion')
        
        if fecha_inicio:
            items = items.filter(fecha_catacion__date__gte=fecha_inicio)
        if fecha_fin:
            items = items.filter(fecha_catacion__date__lte=fecha_fin)

    context = {
        'tipo_historial': tipo_historial,
        'items': items,
        'request': request,
    }
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
    
    lotes = Lote.objects.select_related('bodega').all().order_by('-fecha_ingreso')
    
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

                lote.tipo_cafe = request.POST.get('tipo_cafe')
                lote.bodega_id = request.POST.get('bodega_id')
                lote.percha = request.POST.get('percha', '')
                lote.fila = request.POST.get('fila', '')
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
        'bodegas': Bodega.objects.all(),

    }
    return render(request, 'beneficio/lotes/crear.html', context)

@login_required
def detalle_lote(request, pk):
    """Ver detalle de un lote"""

    lote = get_object_or_404(Lote.objects.select_related('bodega'), pk=pk)
    
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
                lote.percha = request.POST.get('percha', '')
                lote.fila = request.POST.get('fila', '')
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
    """Eliminar un lote (marcar como inactivo)"""
    lote = get_object_or_404(Lote, pk=pk)
    
    if request.method == 'POST':
        codigo = lote.codigo
        lote.activo = False
        lote.save()
        messages.success(request, f'Lote {codigo} marcado como inactivo exitosamente')
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
    """Lista todos los procesados"""
    # Obtener filtros
    fecha = request.GET.get('fecha')
    lote_codigo = request.GET.get('lote')
    year_filter = request.GET.get('year')
    
    procesados = Procesado.objects.select_related('lote', 'lote__bodega', 'operador').all()
    
    if fecha:
        procesados = procesados.filter(fecha__date=fecha)
    
    if lote_codigo:
        procesados = procesados.filter(lote__codigo__icontains=lote_codigo)
    
    if year_filter:
        procesados = procesados.filter(fecha__year=year_filter)
    
    procesados = procesados.order_by('-fecha')
    

    paginator = Paginator(procesados, 10) 
    page = request.GET.get('page')
    procesados_paginados = paginator.get_page(page)

    estadisticas = procesados.aggregate(
        total_entrada=Sum('peso_inicial_kg'),
        total_salida=Sum('peso_final_kg'),
    )
    
    years = Procesado.objects.annotate(
        year=ExtractYear('fecha')
    ).values_list('year', flat=True).distinct().order_by('-year')
    
    context = {
        'procesados': procesados_paginados, # Usar la variable paginada
        'lotes': Lote.objects.all(), # Para el filtro
        'years': years,
        'estadisticas': estadisticas,
    }
    return render(request, 'beneficio/procesados/lista.html', context)

@login_required
def crear_procesado(request, lote_id):
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                peso_a_procesar = Decimal(request.POST.get('peso_inicial_kg'))
                
                peso_disponible = Decimal(str(lote.peso_disponible))
                if peso_a_procesar > peso_disponible:
                    messages.error(
                        request, 
                        f'❌ No puedes procesar {peso_a_procesar} kg. '
                        f'Solo hay {peso_disponible} kg disponibles en el lote.'
                    )
                    return redirect('crear_procesado', lote_id=lote.id)
                
                procesado = Procesado()
                procesado.lote = lote
                
                # Fecha y horas
                fecha_procesado_str = request.POST.get('fecha_procesado')
                if fecha_procesado_str:
                    procesado.fecha = fecha_procesado_str
                
                hora_inicio_str = request.POST.get('hora_inicio')
                if hora_inicio_str:
                    procesado.hora_inicio = hora_inicio_str
                
                hora_final_str = request.POST.get('hora_final')
                if hora_final_str:
                    procesado.hora_final = hora_final_str
                
                procesado.peso_inicial_kg = peso_a_procesar
                procesado.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                procesado.peso_final_kg = Decimal(request.POST.get('peso_final_kg', 0))
                procesado.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                
                procesado.cafe_primera = Decimal(request.POST.get('cafe_primera', 0))
                procesado.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                procesado.cafe_segunda = Decimal(request.POST.get('cafe_segunda', 0))
                procesado.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                
                procesado.catadura = Decimal(request.POST.get('catadura', 0))
                procesado.rechazo_electronica = Decimal(request.POST.get('rechazo_electronica', 0))
                procesado.bajo_zaranda = Decimal(request.POST.get('bajo_zaranda', 0))
                procesado.barridos = Decimal(request.POST.get('barridos', 0))
                
                procesado.observaciones = request.POST.get('observaciones', '')
                procesado.operador = request.user
                
                # Campos adicionales (si existen en tu modelo)
                peso_saco = request.POST.get('peso_saco_referencia', '69')
                if peso_saco:
                    try:
                        procesado.peso_saco_referencia = Decimal(peso_saco)
                    except:
                        pass
                
                unidad_saco = request.POST.get('unidad_saco_referencia', 'kg')
                if hasattr(procesado, 'unidad_saco_referencia'):
                    procesado.unidad_saco_referencia = unidad_saco
                
                # Bodega destino y ubicación
                bodega_destino_id = request.POST.get('bodega_destino')
                if bodega_destino_id and hasattr(procesado, 'bodega_destino'):
                    procesado.bodega_destino_id = bodega_destino_id

                procesado.percha = request.POST.get('percha', '')
                procesado.fila = request.POST.get('fila', '')

                procesado.save()
                
                messages.success(
                    request, 
                    f'✅ Trilla #{procesado.numero_trilla} procesada exitosamente. '
                    f'Quedan {lote.peso_disponible:.2f} kg disponibles en el lote.'
                )
                return redirect('detalle_procesado', pk=procesado.id)
                
        except ValueError as ve:
            messages.error(request, f'❌ Error en los valores ingresados: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error al crear procesado: {str(e)}')
    
    # GET - Mostrar formulario
    context = {
        'lote': lote,
        'bodegas': Bodega.objects.all(),
        'today': timezone.now()
    }
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
                hora_inicio_str = request.POST.get('hora_inicio')
                procesado.hora_inicio = hora_inicio_str if hora_inicio_str else None
                hora_final_str = request.POST.get('hora_final')
                procesado.hora_final = hora_final_str if hora_final_str else None
                
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

                # Ubicación
                bodega_destino_id = request.POST.get('bodega_destino')
                procesado.bodega_destino_id = bodega_destino_id if bodega_destino_id else None
                procesado.percha = request.POST.get('percha', '')
                procesado.fila = request.POST.get('fila', '')

                procesado.save()
                
                messages.success(request, f'Procesado #{procesado.numero_trilla} actualizado exitosamente')
                return redirect('detalle_procesado', pk=procesado.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar procesado: {str(e)}')
    
    context = {
        'procesado': procesado,
        'bodegas': Bodega.objects.all(),
    }
    return render(request, 'beneficio/procesados/editar.html', context)

@login_required
def crear_procesado_desde_recibo(request, recibo_id):
    """
    Crea un Procesado (Trilla) a partir de un ReciboCafe específico.
    El formulario se ve como el de 'procesar lote' pero usa los
    datos del recibo.
    """
    recibo = get_object_or_404(ReciboCafe, pk=recibo_id)
    lote = recibo.lote
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                procesado = Procesado()
                procesado.lote = lote 
                
                # Guardamos el recibo_id en las observaciones para trazabilidad
                observaciones = request.POST.get('observaciones', '')
                observaciones_recibo = f"Procesado desde Recibo: {recibo.numero_recibo} (Proveedor: {recibo.proveedor}).\n\n{observaciones}"
                
                # Asignar todos los campos del formulario
                hora_inicio_str = request.POST.get('hora_inicio')
                if hora_inicio_str:
                    procesado.hora_inicio = hora_inicio_str
                
                hora_final_str = request.POST.get('hora_final')
                if hora_final_str:
                    procesado.hora_final = hora_final_str
                
                procesado.peso_inicial_kg = Decimal(request.POST.get('peso_inicial_kg'))
                procesado.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                procesado.peso_final_kg = Decimal(request.POST.get('peso_final_kg'))
                procesado.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                
                procesado.cafe_primera = Decimal(request.POST.get('cafe_primera', 0))
                procesado.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                procesado.cafe_segunda = Decimal(request.POST.get('cafe_segunda', 0))
                procesado.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                
                procesado.catadura = Decimal(request.POST.get('catadura', 0))
                procesado.rechazo_electronica = Decimal(request.POST.get('rechazo_electronica', 0))
                procesado.bajo_zaranda = Decimal(request.POST.get('bajo_zaranda', 0))
                procesado.barridos = Decimal(request.POST.get('barridos', 0))
                
                procesado.observaciones = observaciones_recibo
                procesado.operador = request.user
                
                procesado.save()
                
                messages.success(request, f'Trilla #{procesado.numero_trilla} creada exitosamente desde el Recibo {recibo.numero_recibo}')
                return redirect('detalle_procesado', pk=procesado.id)
        except Exception as e:
             messages.error(request, f'Error al crear procesado desde recibo: {str(e)}')
    
    context = {
        'lote': lote,
        'bodegas': Bodega.objects.all(),
        'recibo': recibo,
        'peso_sugerido_kg': recibo.convertir_a_kg() 
    }
    return render(request, 'beneficio/procesados/crear_desde_recibo.html', context)
# --- FIN DE LA FUNCIÓN AÑADIDA ---

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
    procesado_id = request.GET.get('procesado') # 'procesado' es el name en el HTML
    
    reprocesos = Reproceso.objects.select_related('procesado__lote', 'operador').all().order_by('-fecha')
    
    if fecha:
        reprocesos = reprocesos.filter(fecha__date=fecha)
    
    if procesado_id:
        reprocesos = reprocesos.filter(procesado_id=procesado_id)
    
    context = {
        'reprocesos': reprocesos,
        'procesados': Procesado.objects.filter(reprocesos__isnull=False).distinct()
    }
    return render(request, 'beneficio/reprocesos/lista.html', context)


@login_required
def crear_reproceso(request, procesado_id):
    """Crear reproceso desde un procesado"""
    procesado = get_object_or_404(Procesado, pk=procesado_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                reproceso = Reproceso()
                reproceso.procesado = procesado
                reproceso.nombre = request.POST.get('nombre', '')
                
                fecha_ingresada = request.POST.get('fecha')
                if fecha_ingresada:
                    reproceso.fecha = fecha_ingresada
                
                reproceso.encargado_reproceso = request.POST.get('encargado_reproceso')
                
                hora_inicio_str = request.POST.get('hora_inicio')
                if hora_inicio_str:
                    reproceso.hora_inicio = hora_inicio_str

                hora_fin_str = request.POST.get('hora_fin')
                if hora_fin_str:
                    reproceso.hora_fin = hora_fin_str

                bodega_destino_id = request.POST.get('bodega_destino')
                if bodega_destino_id:
                    reproceso.bodega_destino_id = bodega_destino_id

                reproceso.percha = request.POST.get('percha', '')
                reproceso.fila = request.POST.get('fila', '')

                reproceso.peso_inicial_kg = request.POST.get('peso_inicial_kg')
                reproceso.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                reproceso.peso_final_kg = request.POST.get('peso_final_kg')
                reproceso.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                reproceso.cafe_primera = request.POST.get('cafe_primera', 0)
                reproceso.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                reproceso.cafe_segunda = request.POST.get('cafe_segunda', 0)
                reproceso.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                reproceso.catadura = request.POST.get('catadura', 0)
                reproceso.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
                reproceso.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
                reproceso.barridos = request.POST.get('barridos', 0)
                reproceso.motivo = request.POST.get('motivo')
                reproceso.operador = request.user
                
                reproceso.save() 
                
                messages.success(request, f'Reproceso #{reproceso.numero} creado exitosamente')
                return redirect('detalle_reproceso', pk=reproceso.id)

        except Exception as e:
            messages.error(request, f'Error al crear reproceso: {e}')
            
    ultimo_reproceso = Reproceso.objects.filter(procesado=procesado).order_by('-numero').first()
    siguiente_numero = (ultimo_reproceso.numero + 1) if ultimo_reproceso else 1
    
    context = {
        'bodegas': Bodega.objects.all(),  
        'procesado': procesado,
        'siguiente_numero': siguiente_numero,
    }
    return render(request, 'beneficio/reprocesos/crear.html', context)


@login_required
def editar_reproceso(request, pk):
    """Vista para editar un reproceso existente"""
    reproceso = get_object_or_404(Reproceso, id=pk)
    bodegas = Bodega.objects.all()
    
    if request.method == 'POST':
        try:

            reproceso.encargado_reproceso = request.POST.get('encargado_reproceso', '')
            reproceso.nombre = request.POST.get('nombre', '')
            reproceso.fecha = request.POST.get('fecha')
            
            # Horarios
            hora_inicio = request.POST.get('hora_inicio')
            hora_fin = request.POST.get('hora_fin')
            reproceso.hora_inicio = hora_inicio if hora_inicio else None
            reproceso.hora_final = hora_fin if hora_fin else None
            
            # Bodega de destino
            bodega_id = request.POST.get('bodega_destino')
            if bodega_id:
                reproceso.bodega_destino = Bodega.objects.get(id=bodega_id)

            # Ubicación
            reproceso.percha = request.POST.get('percha', '')
            reproceso.fila = request.POST.get('fila', '')

            # Pesos
            reproceso.peso_inicial_kg = Decimal(request.POST.get('peso_inicial_kg', '0'))
            reproceso.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
            reproceso.peso_final_kg = Decimal(request.POST.get('peso_final_kg', '0'))
            reproceso.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
            
            # Clasificación de café
            reproceso.cafe_primera = Decimal(request.POST.get('cafe_primera', '0') or '0')
            reproceso.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
            reproceso.cafe_segunda = Decimal(request.POST.get('cafe_segunda', '0') or '0')
            reproceso.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
            
            # Mermas
            reproceso.catadura = Decimal(request.POST.get('catadura', '0') or '0')
            reproceso.rechazo_electronica = Decimal(request.POST.get('rechazo_electronica', '0') or '0')
            reproceso.bajo_zaranda = Decimal(request.POST.get('bajo_zaranda', '0') or '0')
            reproceso.barridos = Decimal(request.POST.get('barridos', '0') or '0')
            
            # Motivo
            reproceso.motivo = request.POST.get('motivo', '')
            
            reproceso.save()
            
            messages.success(request, f'Reproceso #{reproceso.numero} actualizado exitosamente.')
            return redirect('detalle_reproceso', reproceso_id=pk)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el reproceso: {str(e)}')
    
    context = {
        'reproceso': reproceso,
        'bodegas': bodegas,
    }
    return render(request, 'beneficio/reprocesos/editar.html', context)


@login_required
def reprocesar_reproceso(request, pk):
    """Crear un nuevo reproceso a partir de un reproceso existente"""
    reproceso_origen = get_object_or_404(Reproceso, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                nuevo_reproceso = Reproceso()
                nuevo_reproceso.procesado = reproceso_origen.procesado
                # 'numero' se genera en el save()
                nuevo_reproceso.nombre = request.POST.get('nombre', f'Re-reproceso de #{reproceso_origen.numero}')
                
                # Tu models.py original SÍ tiene estos campos:
                nuevo_reproceso.encargado_reproceso = request.POST.get('encargado_reproceso')
                
                hora_inicio_str = request.POST.get('hora_inicio')
                if hora_inicio_str:
                    nuevo_reproceso.hora_inicio = hora_inicio_str

                hora_fin_str = request.POST.get('hora_fin')
                if hora_fin_str:
                    nuevo_reproceso.hora_fin = hora_fin_str
                
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
        'bodegas': Bodega.objects.all(),  
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
    mezclas = Mezcla.objects.select_related('responsable').all().order_by('-fecha')
    
    context = {
        'mezclas': mezclas,
    }
    return render(request, 'beneficio/mezclas/lista.html', context)


@login_required
def crear_mezcla(request):
    """Crear nueva mezcla (LÓGICA ORIGINAL)"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                mezcla = Mezcla()
                # 'numero' se genera en el save()
                
                fecha_ingresada = request.POST.get('fecha')
                if fecha_ingresada:
                    mezcla.fecha = fecha_ingresada
                

                mezcla.hora_inicio = request.POST.get('hora_inicio') or None
                mezcla.hora_final = request.POST.get('hora_final') or None
                bodega_destino_id = request.POST.get('bodega_destino')
                if bodega_destino_id:
                    mezcla.bodega_destino_id = bodega_destino_id

                mezcla.percha = request.POST.get('percha', '')
                mezcla.fila = request.POST.get('fila', '')

                mezcla.descripcion = request.POST.get('descripcion', '')
                mezcla.destino = request.POST.get('destino', '')
                mezcla.responsable = request.user
                mezcla.save()
                
                componentes = json.loads(request.POST.get('componentes', '[]'))
                
                peso_total = Decimal(0)
                for comp in componentes:

                    lote_id = comp.get('lote_id')
                    peso = Decimal(comp.get('peso', 0))
                    
                    if lote_id and peso > 0:
                        lote = get_object_or_404(Lote, pk=lote_id)
                        peso_total += peso
                        
                        DetalleMezcla.objects.create(
                            mezcla=mezcla,
                            lote=lote,
                            peso_kg=peso,
                            porcentaje=0 
                        )
                
                if peso_total > 0:
                    for detalle in mezcla.detalles.all():
                        detalle.porcentaje = (Decimal(detalle.peso_kg) / peso_total) * 100
                        detalle.save()
                
                mezcla.peso_total_kg = peso_total
                mezcla.save()
                
                messages.success(request, f'Mezcla #{mezcla.numero} creada exitosamente')
                return redirect('detalle_mezcla', pk=mezcla.id)
                
        except Exception as e:
            messages.error(request, f'Error al crear mezcla: {str(e)}')
    
    
    opciones_mezcla = []
    
    # 1. LOTES
    for lote in Lote.objects.filter(activo=True):
        opciones_mezcla.append({
            'lote_id': lote.id, 
            'tipo': '📦 Lote',
            'codigo': lote.codigo,
            'descripcion': f"{lote.tipo_cafe} - Bodega {lote.bodega.codigo}",
            'peso_disponible': float(lote.peso_kg)
        })
    
    # 2. PROCESADOS
    for procesado in Procesado.objects.select_related('lote').all():
        opciones_mezcla.append({
            'lote_id': procesado.lote.id, 
            'tipo': '⚙️ Procesado',
            'codigo': f"Trilla #{procesado.numero_trilla}",
            'descripcion': f"Lote {procesado.lote.codigo} - {procesado.lote.tipo_cafe}",
            'peso_disponible': float(procesado.peso_final_kg)
        })
    
    # 3. REPROCESOS
    for reproceso in Reproceso.objects.select_related('procesado__lote').all():
        nombre = reproceso.nombre if reproceso.nombre else f"Reproceso #{reproceso.numero}"
        opciones_mezcla.append({
            'lote_id': reproceso.procesado.lote.id, 
            'tipo': '🔄 Reproceso',
            'codigo': nombre,
            'descripcion': f"Lote {reproceso.procesado.lote.codigo} - De Trilla #{reproceso.procesado.numero_trilla}",
            'peso_disponible': float(reproceso.peso_final_kg)
        })
    
    context = {
        'bodegas': Bodega.objects.all(), 
        'opciones_json': json.dumps(opciones_mezcla),
        'total_opciones': len(opciones_mezcla)
    }
    return render(request, 'beneficio/mezclas/crear.html', context)

@login_required
def detalle_mezcla(request, pk):
    """Ver detalle de una mezcla"""
    mezcla = get_object_or_404(Mezcla, pk=pk)
    detalles = mezcla.detalles.select_related('lote__bodega').all()
    
    context = {
        'mezcla': mezcla,
        'detalles': detalles,
    }
    return render(request, 'beneficio/mezclas/detalle.html', context)


@login_required
def editar_mezcla(request, pk):
    """Editar una mezcla (Lógica de edición de componentes no implementada)"""
    mezcla = get_object_or_404(Mezcla, pk=pk)
    
    if request.method == 'POST':
        try:
            mezcla.descripcion = request.POST.get('descripcion', '')
            mezcla.destino = request.POST.get('destino', '')

            # Ubicación
            bodega_destino_id = request.POST.get('bodega_destino')
            mezcla.bodega_destino_id = bodega_destino_id if bodega_destino_id else None
            mezcla.percha = request.POST.get('percha', '')
            mezcla.fila = request.POST.get('fila', '')

            mezcla.save()
            messages.success(request, 'Mezcla actualizada exitosamente')
            return redirect('detalle_mezcla', pk=mezcla.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')

    context = {
        'mezcla': mezcla,
        'bodegas': Bodega.objects.all(),
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

@login_required
def crear_catacion(request):
    """Vista para crear una nueva catación"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                
                catacion = Catacion()
                catacion.tipo_muestra = request.POST.get('tipo_muestra')

                if catacion.tipo_muestra == 'lote':
                    catacion.lote_id = request.POST.get('lote_id')
                elif catacion.tipo_muestra == 'procesado':
                    catacion.procesado_id = request.POST.get('procesado_id')
                elif catacion.tipo_muestra == 'reproceso':
                    catacion.reproceso_id = request.POST.get('reproceso_id')
                elif catacion.tipo_muestra == 'mezcla':
                    catacion.mezcla_id = request.POST.get('mezcla_id')
                elif catacion.tipo_muestra == 'partida':
                    catacion.partida_id = request.POST.get('partida_id')
                
                fecha_catacion_str = request.POST.get('fecha_catacion')
                if fecha_catacion_str:
                    catacion.fecha_catacion = fecha_catacion_str
                
                catacion.catador = request.user
                
                # Parámetros de catación
                catacion.peso_muestra_g = request.POST.get('peso_muestra_g', 8.25)
                catacion.temperatura_agua = request.POST.get('temperatura_agua', 93.0)
                catacion.tiempo_infusion = request.POST.get('tiempo_infusion', 4)
                catacion.tipo_tueste = request.POST.get('tipo_tueste', 'medio')
                
                humedad_str = request.POST.get('humedad_grano')
                if humedad_str:
                    catacion.humedad_grano = Decimal(humedad_str)
                
                # ============================================
                # PUNTAJES AFECTIVOS (PARTE 2) - CORREGIDO
                # ============================================
                catacion.fragancia_aroma = Decimal(request.POST.get('fragancia_aroma', '0'))
                catacion.sabor = Decimal(request.POST.get('sabor', '0'))
                catacion.sabor_residual = Decimal(request.POST.get('sabor_residual', '0'))
                catacion.acidez = Decimal(request.POST.get('acidez', '0'))
                catacion.cuerpo = Decimal(request.POST.get('cuerpo', '0'))
                catacion.uniformidad = Decimal(request.POST.get('uniformidad', '10'))
                catacion.balance = Decimal(request.POST.get('balance', '0'))
                catacion.taza_limpia = Decimal(request.POST.get('taza_limpia', '10'))
                catacion.dulzor = Decimal(request.POST.get('dulzor', '10'))
                catacion.puntaje_catador = Decimal(request.POST.get('puntaje_catador', '0'))
                
                # ============================================
                # EVALUACIÓN DESCRIPTIVA (PARTE 1)
                # ============================================
                catacion.intensidad_fragancia = request.POST.get('intensidad_fragancia', 5)
                catacion.intensidad_aroma = request.POST.get('intensidad_aroma', 5)
                catacion.intensidad_sabor = request.POST.get('intensidad_sabor', 5)
                catacion.intensidad_sabor_residual = request.POST.get('intensidad_sabor_residual', 5)
                catacion.intensidad_acidez = request.POST.get('intensidad_acidez', 5)
                catacion.intensidad_cuerpo = request.POST.get('intensidad_cuerpo', 5)
                
                # Atributos de Fragancia/Aroma
                catacion.attr_floral = request.POST.get('attr_floral') == 'on'
                catacion.attr_afrutado = request.POST.get('attr_afrutado') == 'on'
                catacion.attr_verde_vegetal = request.POST.get('attr_verde_vegetal') == 'on'
                catacion.attr_tostado = request.POST.get('attr_tostado') == 'on'
                catacion.attr_nueces_cacao = request.POST.get('attr_nueces_cacao') == 'on'
                catacion.attr_dulce = request.POST.get('attr_dulce') == 'on'
                catacion.attr_especias = request.POST.get('attr_especias') == 'on'
                catacion.attr_acido_fermentado = request.POST.get('attr_acido_fermentado') == 'on'
                
                # Gustos básicos
                catacion.gusto_salado = request.POST.get('gusto_salado') == 'on'
                catacion.gusto_acido = request.POST.get('gusto_acido') == 'on'
                catacion.gusto_dulce = request.POST.get('gusto_dulce') == 'on'
                catacion.gusto_amargo = request.POST.get('gusto_amargo') == 'on'
                catacion.gusto_umami = request.POST.get('gusto_umami') == 'on'
                
                # Atributos de cuerpo
                catacion.cuerpo_aspero = request.POST.get('cuerpo_aspero') == 'on'
                catacion.cuerpo_aceitoso = request.POST.get('cuerpo_aceitoso') == 'on'
                catacion.cuerpo_suave = request.POST.get('cuerpo_suave') == 'on'
                catacion.cuerpo_seca_boca = request.POST.get('cuerpo_seca_boca') == 'on'
                catacion.cuerpo_metalico = request.POST.get('cuerpo_metalico') == 'on'
                
                # Notas descriptivas
                catacion.notas_fragancia_aroma = request.POST.get('notas_fragancia_aroma', '')
                catacion.notas_sabor = request.POST.get('notas_sabor', '')
                catacion.notas_residual = request.POST.get('notas_residual', '')
                catacion.notas_acidez = request.POST.get('notas_acidez', '')
                catacion.notas_cuerpo = request.POST.get('notas_cuerpo', '')
                
                # ============================================
                # NOTAS AFECTIVAS INDIVIDUALES
                # ============================================
                catacion.notas_fragancia = request.POST.get('notas_fragancia', '')
                catacion.notas_aroma = request.POST.get('notas_aroma', '')
                catacion.notas_sabor_afectivo = request.POST.get('notas_sabor_afectivo', '')
                catacion.notas_residual_afectivo = request.POST.get('notas_residual_afectivo', '')
                catacion.notas_acidez_afectivo = request.POST.get('notas_acidez_afectivo', '')
                catacion.notas_cuerpo_afectivo = request.POST.get('notas_cuerpo_afectivo', '')
                catacion.notas_balance = request.POST.get('notas_balance', '')
                catacion.notas_general = request.POST.get('notas_general', '')
                
                # ============================================
                # EVALUACIÓN EXTRÍNSECA (PARTE 3)
                # ============================================
                catacion.notas_extrinseca = request.POST.get('notas_extrinseca', '')
                catacion.notas_perfil = request.POST.get('notas_perfil', '')
                catacion.notas_catador = request.POST.get('notas_catador', '')
                
                # Información de origen
                catacion.productor = request.POST.get('productor', '')
                catacion.altitud = request.POST.get('altitud', '')
                catacion.region = request.POST.get('region', '')
                catacion.variedad = request.POST.get('variedad', '')
                catacion.proceso = request.POST.get('proceso', '')
                catacion.secado = request.POST.get('secado', '')
                catacion.horas_fermentacion = request.POST.get('horas_fermentacion', '')
                catacion.finca = request.POST.get('finca', '')
                
                # ============================================
                # GRANULOMETRÍA
                # ============================================
                catacion.gran_10 = Decimal(request.POST.get('gran_10', '0') or '0')
                catacion.gran_11 = Decimal(request.POST.get('gran_11', '0') or '0')
                catacion.gran_12 = Decimal(request.POST.get('gran_12', '0') or '0')
                catacion.gran_13 = Decimal(request.POST.get('gran_13', '0') or '0')
                catacion.gran_14 = Decimal(request.POST.get('gran_14', '0') or '0')
                catacion.gran_15 = Decimal(request.POST.get('gran_15', '0') or '0')
                catacion.gran_16 = Decimal(request.POST.get('gran_16', '0') or '0')
                catacion.gran_17 = Decimal(request.POST.get('gran_17', '0') or '0')
                catacion.gran_18 = Decimal(request.POST.get('gran_18', '0') or '0')
                catacion.gran_19 = Decimal(request.POST.get('gran_19', '0') or '0')
                catacion.gran_20 = Decimal(request.POST.get('gran_20', '0') or '0')
                catacion.gran_21 = Decimal(request.POST.get('gran_21', '0') or '0')
                
                catacion.peso_muestra_granulometria = request.POST.get('peso_muestra_granulometria', '')
                catacion.actividad_agua = request.POST.get('actividad_agua', '')
                catacion.observaciones_granulometria = request.POST.get('observaciones_granulometria', '')
                
                # Colores de granulometría - CORREGIDO
                catacion.color_azul_verde = request.POST.get('color_azul_verde') == 'on'
                catacion.color_verde_azulado = request.POST.get('color_verde_azulado') == 'on'
                catacion.color_verde = request.POST.get('color_verde') == 'on'
                catacion.color_verde_amarillento = request.POST.get('color_verde_amarillento') == 'on'
                catacion.color_amarillo_verdoso = request.POST.get('color_amarillo_verdoso') == 'on'
                catacion.color_amarillo = request.POST.get('color_amarillo') == 'on'
                catacion.color_cafe = request.POST.get('color_cafe') == 'on'
                catacion.color_otro = request.POST.get('color_otro') == 'on'
                
                # ============================================
                # DEFECTOS
                # ============================================
                catacion.defectos_intensidad_2 = int(request.POST.get('defectos_intensidad_2', '0'))
                catacion.defectos_intensidad_4 = int(request.POST.get('defectos_intensidad_4', '0'))
                catacion.descripcion_defectos = request.POST.get('descripcion_defectos', '')

                catacion.save()

                # --- Crear DefectoCatacion relacionado ---
                if catacion.defectos_intensidad_2 > 0:
                    DefectoCatacion.objects.create(
                        catacion=catacion,
                        categoria='secundario', 
                        tipo_defecto='Defecto(s) Int. 2',
                        cantidad=catacion.defectos_intensidad_2,
                        equivalente_defectos=Decimal(catacion.defectos_intensidad_2 * 2)
                    )
                if catacion.defectos_intensidad_4 > 0:
                    DefectoCatacion.objects.create(
                        catacion=catacion,
                        categoria='primario',
                        tipo_defecto='Defecto(s) Int. 4',
                        cantidad=catacion.defectos_intensidad_4,
                        equivalente_defectos=Decimal(catacion.defectos_intensidad_4 * 4)
                    )
                
                messages.success(request, f'Catación {catacion.codigo_muestra} creada exitosamente.')
                return redirect('detalle_catacion', pk=catacion.pk)

        except Exception as e:
            messages.error(request, f'Error al guardar la catación: {e}')
            context = {
                'lotes': Lote.objects.all(),
                'procesados': Procesado.objects.all(),
                'mezclas': Mezcla.objects.all(),
                'reprocesos': Reproceso.objects.all(),
                'partidas': Partida.objects.filter(activo=True),
                'form_data': request.POST
            }
            return render(request, 'beneficio/catacion/crear.html', context)

    # --- GET - Mostrar formulario ---
    tipo_preseleccionado = request.GET.get('tipo', '')
    partida_id_preseleccionada = request.GET.get('partida_id', '')

    context = {
        'lotes': Lote.objects.filter(activo=True),
        'procesados': Procesado.objects.all(),
        'mezclas': Mezcla.objects.all(),
        'reprocesos': Reproceso.objects.all(),
        'partidas': Partida.objects.filter(activo=True),
        'tipo_preseleccionado': tipo_preseleccionado,
        'partida_id_preseleccionada': partida_id_preseleccionada,
    }
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
def detalle_reproceso(request, pk):
    """Ver detalle de un reproceso"""
    reproceso = get_object_or_404(Reproceso, pk=pk)
    
    context = {
        'reproceso': reproceso,
    }
    return render(request, 'beneficio/reprocesos/detalle.html', context)


@login_required
def continuar_procesado(request, procesado_id):
    """Vista para continuar/editar un procesado existente con datos precargados"""
    
    procesado = get_object_or_404(Procesado, id=procesado_id)
    lote = procesado.lote
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Actualizar fecha y hora
                fecha = request.POST.get('fecha')
                if fecha:
                    procesado.fecha = fecha
                
                hora_inicio = request.POST.get('hora_inicio')
                hora_final = request.POST.get('hora_final')
                if hora_inicio:
                    procesado.hora_inicio = hora_inicio
                if hora_final:
                    procesado.hora_final = hora_final
                
                # Actualizar peso inicial
                peso_inicial_kg = request.POST.get('peso_inicial_kg')
                if peso_inicial_kg:
                    procesado.peso_inicial_kg = Decimal(peso_inicial_kg)
                
                # Actualizar peso final
                peso_final_kg = request.POST.get('peso_final_kg')
                if peso_final_kg:
                    procesado.peso_final_kg = Decimal(peso_final_kg)
                
                # Actualizar humedad
                humedad_inicial = request.POST.get('humedad_inicial')
                humedad_final = request.POST.get('humedad_final')
                if humedad_inicial:
                    procesado.humedad_inicial = Decimal(humedad_inicial)
                if humedad_final:
                    procesado.humedad_final = Decimal(humedad_final)
                
                # Actualizar café primera
                cafe_primera = request.POST.get('cafe_primera')
                unidad_cafe_primera = request.POST.get('unidad_cafe_primera')
                if cafe_primera:
                    procesado.cafe_primera = Decimal(cafe_primera)
                    procesado.unidad_cafe_primera = unidad_cafe_primera
                
                # Actualizar café segunda
                cafe_segunda = request.POST.get('cafe_segunda')
                unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda')
                if cafe_segunda:
                    procesado.cafe_segunda = Decimal(cafe_segunda)
                    procesado.unidad_cafe_segunda = unidad_cafe_segunda
                
                # Actualizar subproductos
                subproductos = ['cascara', 'pergamino', 'cisco', 'cafe_caracol']
                for subprod in subproductos:
                    valor = request.POST.get(subprod)
                    if valor:
                        setattr(procesado, subprod, Decimal(valor))
                
                # Actualizar encargado y trabajadores
                encargado = request.POST.get('encargado_trilla')
                trabajadores = request.POST.get('trabajadores')
                if encargado:
                    procesado.encargado_trilla = encargado
                if trabajadores:
                    procesado.trabajadores = int(trabajadores)
                
                # Actualizar observaciones
                observaciones = request.POST.get('observaciones')
                if observaciones:
                    procesado.observaciones = observaciones
                
                procesado.save()
                
                messages.success(
                    request,
                    f'Procesado #{procesado.numero_trilla} actualizado exitosamente.'
                )
                
                return redirect('detalle_procesado', procesado_id=procesado.id)
                
        except ValueError as e:
            messages.error(request, f'Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al actualizar procesado: {str(e)}')
    
    context = {
        'procesado': procesado,
        'lote': lote,
    }
    
    return render(request, 'beneficio/procesados/continuar.html', context)


@login_required
def seleccionar_lote_procesar(request):
    """Vista para seleccionar el lote a procesar (CON FILTROS)"""
    
    lotes = Lote.objects.select_related('bodega').filter(activo=True)
    
    codigo = request.GET.get('codigo')
    tipo_cafe_nombre = request.GET.get('tipo') 
    bodega_codigo = request.GET.get('bodega')
    estado_proceso = request.GET.get('estado_proceso')

    if codigo:
        lotes = lotes.filter(codigo__icontains=codigo)
    
    if tipo_cafe_nombre:
        lotes = lotes.filter(tipo_cafe__icontains=tipo_cafe_nombre)
    
    if bodega_codigo:
        lotes = lotes.filter(bodega__codigo=bodega_codigo)
        
    if estado_proceso == 'sin_procesar':
        lotes = lotes.filter(procesos__isnull=True)
    elif estado_proceso == 'procesado':
        lotes = lotes.filter(procesos__isnull=False).distinct()

    
    context = {
        'lotes': lotes,
        'bodegas': Bodega.objects.all(),
    }
    return render(request, 'beneficio/procesados/seleccionar_lote.html', context)

@login_required
def imprimir_catacion(request, pk):
    catacion = get_object_or_404(Catacion, pk=pk)
    context = {'catacion': catacion}
    return render(request, 'beneficio/catacion/imprimir.html', context)

@login_required
def lista_cataciones(request):
    """Vista para listar todas las cataciones"""
    cataciones = Catacion.objects.select_related(
        'lote', 
        'procesado__lote', 
        'reproceso__procesado__lote', 
        'mezcla', 
        'catador'
    ).order_by('-fecha_catacion')
    
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
        cataciones = cataciones.filter(fecha_catacion__date__gte=fecha_desde)
    if fecha_hasta:
        cataciones = cataciones.filter(fecha_catacion__date__lte=fecha_hasta)
    if puntaje_min:
        cataciones = cataciones.filter(puntaje_total__gte=puntaje_min)

    context = {
        'cataciones': cataciones,
    }
    return render(request, 'beneficio/catacion/lista.html', context)

# ==========================================
# VISTAS DE COMPRADORES Y COMPRAS
# ==========================================

@login_required
def lista_compradores(request):
    """Lista todos los compradores"""
    nombre = request.GET.get('nombre')
    estado = request.GET.get('estado')
    
    compradores = Comprador.objects.all()
    
    if nombre:
        compradores = compradores.filter(
            Q(nombre__icontains=nombre) | Q(empresa__icontains=nombre)
        )
    
    if estado == 'activo':
        compradores = compradores.filter(activo=True)
    elif estado == 'inactivo':
        compradores = compradores.filter(activo=False)
    
    compradores = compradores.annotate(
        num_compras=Count('compras'),
        total_comprado=Sum('compras__monto_total')
    ).order_by('nombre')
    
    context = {
        'compradores': compradores,
    }
    return render(request, 'beneficio/compradores/lista.html', context)



@login_required
def crear_comprador(request):
    """Crear nuevo comprador"""
    if request.method == 'POST':
        try:
            comprador = Comprador()
            comprador.nombre = request.POST.get('nombre')
            comprador.empresa = request.POST.get('empresa', '')
            comprador.telefono = request.POST.get('telefono', '')
            comprador.email = request.POST.get('email', '')
            comprador.direccion = request.POST.get('direccion', '')
            comprador.notas = request.POST.get('notas', '')
            comprador.created_by = request.user
            comprador.save()
            
            messages.success(request, f'Comprador {comprador.nombre} creado exitosamente')
            return redirect('detalle_comprador', pk=comprador.pk)
        except Exception as e:
            messages.error(request, f'Error al crear comprador: {str(e)}')
    
    return render(request, 'beneficio/compradores/crear.html')


@login_required
def detalle_comprador(request, pk):
    """Ver detalle de un comprador"""
    comprador = get_object_or_404(Comprador, pk=pk)
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    estado_pago = request.GET.get('estado_pago')
    
    compras = comprador.compras.all()
    
    if fecha_desde:
        compras = compras.filter(fecha_compra__date__gte=fecha_desde)
    if fecha_hasta:
        compras = compras.filter(fecha_compra__date__lte=fecha_hasta)
    if estado_pago:
        compras = compras.filter(estado_pago=estado_pago)
    
    estadisticas_filtradas = compras.aggregate(
        total_compras=Count('id'),
        monto_total=Sum('monto_total'),
        cantidad_total=Sum('cantidad')
    )
    
    context = {
        'comprador': comprador,
        'compras': compras.order_by('-fecha_compra'),
        'total_compras': estadisticas_filtradas['total_compras'] or 0,
        'cantidad_total': estadisticas_filtradas['cantidad_total'] or 0,
        'monto_total': estadisticas_filtradas['monto_total'] or 0,
    }
    return render(request, 'beneficio/compradores/detalle.html', context)

@login_required
def editar_comprador(request, pk):
    """Editar un comprador"""
    comprador = get_object_or_404(Comprador, pk=pk)
    
    if request.method == 'POST':
        try:
            comprador.nombre = request.POST.get('nombre')
            comprador.empresa = request.POST.get('empresa', '')
            comprador.telefono = request.POST.get('telefono', '')
            comprador.email = request.POST.get('email', '')
            comprador.direccion = request.POST.get('direccion', '')
            comprador.notas = request.POST.get('notas', '')
            comprador.save()
            
            messages.success(request, f'Comprador {comprador.nombre} actualizado exitosamente')
            return redirect('detalle_comprador', pk=comprador.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar comprador: {str(e)}')
    
    context = {
        'comprador': comprador,
    }
    return render(request, 'beneficio/compradores/editar.html', context)

@login_required
def eliminar_comprador(request, pk):
    """Desactivar un comprador"""
    comprador = get_object_or_404(Comprador, pk=pk)
    
    if request.method == 'POST':
        comprador.activo = False
        comprador.save()
        messages.success(request, f'Comprador {comprador.nombre} desactivado exitosamente')
        return redirect('lista_compradores')
    
    context = {
        'comprador': comprador,
    }
    return render(request, 'beneficio/compradores/eliminar.html', context)

@login_required
def agregar_compra(request, comprador_id):
    """Agregar nueva compra a un comprador"""
    comprador = get_object_or_404(Comprador, pk=comprador_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                compra = Compra()
                compra.comprador = comprador
                
                fecha_compra_str = request.POST.get('fecha_compra')
                compra.fecha_compra = fecha_compra_str if fecha_compra_str else timezone.now()
                
                compra.descripcion = request.POST.get('descripcion', '')
                
                compra.cantidad = Decimal(request.POST.get('cantidad'))
                compra.precio_unitario = Decimal(request.POST.get('precio_unitario'))
                
                compra.unidad = request.POST.get('unidad')
                compra.numero_factura = request.POST.get('numero_factura', '')
                compra.metodo_pago = request.POST.get('metodo_pago', '')
                compra.estado_pago = request.POST.get('estado_pago', 'pendiente')

                # Manejar archivo comprobante
                if 'comprobante' in request.FILES:
                    compra.comprobante = request.FILES['comprobante']

                lote_id = request.POST.get('lote_id')
                procesado_id = request.POST.get('procesado_id')
                mezcla_id = request.POST.get('mezcla_id')
                
                compra.lote_id = lote_id if lote_id else None
                compra.procesado_id = procesado_id if procesado_id else None
                compra.mezcla_id = mezcla_id if mezcla_id else None
                
                compra.registrado_por = request.user
                
                compra.save()
                
                messages.success(request, f'Compra agregada exitosamente a {comprador.nombre}')
                return redirect('detalle_comprador', pk=comprador.pk)
        except Exception as e:
            messages.error(request, f'Error al agregar compra: {str(e)}')
    
    context = {
        'comprador': comprador,
        'lotes': Lote.objects.filter(activo=True),
        'procesados': Procesado.objects.all(),
        'mezclas': Mezcla.objects.all(),
    }
    return render(request, 'beneficio/compradores/agregar_compra.html', context)


@login_required
def editar_compra(request, pk):
    """Editar una compra existente"""
    compra = get_object_or_404(Compra, pk=pk)
    
    if request.method == 'POST':
        try:
            cantidad = Decimal(request.POST.get('cantidad'))
            precio_unitario = Decimal(request.POST.get('precio_unitario'))
            
            compra.fecha_compra = request.POST.get('fecha_compra')
            compra.cantidad = cantidad
            compra.unidad = request.POST.get('unidad', 'qq')
            compra.precio_unitario = precio_unitario
            compra.descripcion = request.POST.get('descripcion', '')
            compra.numero_factura = request.POST.get('numero_factura', '')
            compra.metodo_pago = request.POST.get('metodo_pago', '')
            compra.estado_pago = request.POST.get('estado_pago', 'pendiente')

            # Manejar archivo comprobante
            if 'comprobante' in request.FILES:
                compra.comprobante = request.FILES['comprobante']

            compra.monto_total = cantidad * precio_unitario

            compra.lote_id = request.POST.get('lote_id') or None
            compra.procesado_id = request.POST.get('procesado_id') or None
            compra.mezcla_id = request.POST.get('mezcla_id') or None
            
            compra.save()

            messages.success(request, 'Compra actualizada exitosamente')
            return redirect('detalle_comprador', pk=compra.comprador.pk)
        
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    context = {
        'compra': compra,
        'lotes': Lote.objects.filter(activo=True),
        'procesados': Procesado.objects.all()[:50],
        'mezclas': Mezcla.objects.all()[:50],
    }
    return render(request, 'beneficio/compradores/editar_compra.html', context)


@login_required
def eliminar_compra(request, pk):
    """Eliminar una compra"""
    compra = get_object_or_404(Compra, pk=pk)
    comprador = compra.comprador

    if request.method == 'POST':
        compra.delete()
        messages.success(request, 'Compra eliminada exitosamente')
        # CORREGIDO: Redirección a lista_compras
        return redirect('lista_compras')

    context = {
        'compra': compra,
    }
    return render(request, 'beneficio/compradores/eliminar_compra.html', context)


@login_required
def cambiar_estado_compras_masivo(request):
    """Cambiar el estado de pago de múltiples compras"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    try:
        import json
        data = json.loads(request.body)
        compras_ids = data.get('compras_ids', [])
        nuevo_estado = data.get('nuevo_estado', '')

        if not compras_ids:
            return JsonResponse({'success': False, 'error': 'No se seleccionaron compras'})

        if nuevo_estado not in ['pagado', 'parcial', 'pendiente']:
            return JsonResponse({'success': False, 'error': 'Estado de pago inválido'})

        # Actualizar las compras
        compras_actualizadas = Compra.objects.filter(pk__in=compras_ids).update(estado_pago=nuevo_estado)

        return JsonResponse({
            'success': True,
            'message': f'{compras_actualizadas} compra(s) actualizada(s)',
            'actualizadas': compras_actualizadas
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def lista_compras(request):
    """Vista general de todas las compras"""
    compras = Compra.objects.select_related(
        'comprador',
        'lote__bodega',
        'procesado__lote__bodega',
        'mezcla'
    ).all().order_by('-fecha_compra')

    # Filtros
    comprador_id = request.GET.get('comprador')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    estado_pago = request.GET.get('estado_pago')
    metodo_pago = request.GET.get('metodo_pago')

    if comprador_id:
        compras = compras.filter(comprador_id=comprador_id)
    if fecha_desde:
        compras = compras.filter(fecha_compra__date__gte=fecha_desde)
    if fecha_hasta:
        compras = compras.filter(fecha_compra__date__lte=fecha_hasta)
    if estado_pago:
        compras = compras.filter(estado_pago=estado_pago)
    if metodo_pago:
        compras = compras.filter(metodo_pago=metodo_pago)

    # Estadísticas
    estadisticas = compras.aggregate(
        total_cantidad=Sum('cantidad'),
        total_monto=Sum('monto_total'),
        total_compras=Count('id')
    )

    context = {
        'compras': compras,
        'compradores': Comprador.objects.filter(activo=True),
        'estadisticas': estadisticas,
        'metodos_pago': Compra.METODO_PAGO_CHOICES,
    }
    return render(request, 'beneficio/compradores/lista_compras.html', context)


@login_required
def comparar_compradores(request):
    """Comparar múltiples compradores seleccionados"""

    # Si es POST, procesamos la comparación
    if request.method == 'POST':
        compradores_ids = request.POST.getlist('compradores')

        if not compradores_ids:
            messages.warning(request, 'Debes seleccionar al menos un comprador para comparar')
            return redirect('comparar_compradores')

        # Obtener compradores seleccionados
        compradores = Comprador.objects.filter(id__in=compradores_ids, activo=True)

        # Preparar datos de comparación
        comparacion_data = []

        for comprador in compradores:
            # Obtener todas las compras del comprador
            compras = Compra.objects.filter(comprador=comprador)

            # Calcular estadísticas
            stats = compras.aggregate(
                total_compras=Count('id'),
                total_cantidad=Sum('cantidad'),
                total_monto=Sum('monto_total'),
                precio_promedio=Avg('precio_unitario')
            )

            # Calcular peso total en kg (convertir según unidad)
            peso_total_kg = 0
            for compra in compras:
                cantidad = float(compra.cantidad or 0)
                if compra.unidad == 'kg':
                    peso_total_kg += cantidad
                elif compra.unidad == 'qq':
                    peso_total_kg += cantidad * 46  # Convertir quintales a kg
                elif compra.unidad == 'lb':
                    peso_total_kg += cantidad * 0.453592  # Convertir libras a kg
                else:
                    # Para sacos u otras unidades, usar cantidad directamente
                    peso_total_kg += cantidad

            comparacion_data.append({
                'comprador': comprador,
                'total_compras': stats['total_compras'] or 0,
                'total_cantidad': stats['total_cantidad'] or 0,
                'total_monto': stats['total_monto'] or 0,
                'precio_promedio': stats['precio_promedio'] or 0,
                'peso_total_kg': peso_total_kg,
                'peso_quintales': peso_total_kg / 46 if peso_total_kg > 0 else 0,
                'ultima_compra': compras.order_by('-fecha_compra').first(),
            })

        # Calcular totales generales
        total_compras_suma = sum(d['total_compras'] for d in comparacion_data)
        total_peso_qq_suma = sum(d['peso_quintales'] for d in comparacion_data)
        total_monto_suma = sum(d['total_monto'] for d in comparacion_data)

        context = {
            'comparacion_data': comparacion_data,
            'total_compradores': len(comparacion_data),
            'total_compras_suma': total_compras_suma,
            'total_peso_qq_suma': total_peso_qq_suma,
            'total_monto_suma': total_monto_suma,
        }

        return render(request, 'beneficio/compradores/comparacion_resultado.html', context)

    # Si es GET, mostrar formulario de selección
    compradores = Comprador.objects.filter(activo=True).annotate(
        total_compras=Count('compras'),
        monto_total=Sum('compras__monto_total')
    ).order_by('-monto_total')

    context = {
        'compradores': compradores,
    }

    return render(request, 'beneficio/compradores/comparar.html', context)


# ==========================================
# VISTAS DE VENTA RÁPIDA (FORMULARIO UNIFICADO)
# ==========================================

@login_required
@transaction.atomic
def registrar_venta(request):
    """
    Vista unificada para registrar una venta, permitiendo
    seleccionar un comprador existente o crear uno nuevo al mismo tiempo.
    """
    
    if request.method == 'POST':
        try:
            # --- 1. Determinar el Comprador ---
            comprador_id = request.POST.get('comprador_id')
            
            if comprador_id:
                comprador = get_object_or_404(Comprador, pk=comprador_id)
            else:
                nombre_nuevo = request.POST.get('nombre_nuevo')
                if not nombre_nuevo:
                    raise Exception("Debe seleccionar un comprador existente o ingresar un nombre para el nuevo comprador.")
                
                comprador = Comprador.objects.create(
                    nombre=nombre_nuevo,
                    empresa=request.POST.get('empresa_nuevo', ''),
                    telefono=request.POST.get('telefono_nuevo', ''),
                    email=request.POST.get('email_nuevo', ''),
                    created_by=request.user
                )
                messages.success(request, f'Nuevo comprador "{comprador.nombre}" creado exitosamente.')

            # --- 2. Crear la Compra ---
            compra = Compra()
            compra.comprador = comprador
            
            fecha_compra_str = request.POST.get('fecha_compra')
            compra.fecha_compra = fecha_compra_str if fecha_compra_str else timezone.now()

            compra.cantidad = Decimal(request.POST.get('cantidad'))
            compra.unidad = request.POST.get('unidad', 'qq')
            compra.precio_unitario = Decimal(request.POST.get('precio_unitario'))
            compra.descripcion = request.POST.get('descripcion', '')
            compra.estado_pago = request.POST.get('estado_pago', 'pendiente')
            
            lote_id = request.POST.get('lote_id')
            procesado_id = request.POST.get('procesado_id')
            mezcla_id = request.POST.get('mezcla_id')
            
            compra.lote_id = lote_id if lote_id else None
            compra.procesado_id = procesado_id if procesado_id else None
            compra.mezcla_id = mezcla_id if mezcla_id else None
            
            compra.registrado_por = request.user
            compra.save() # monto_total se calcula en el .save()

            messages.success(request, f'Compra de Q{compra.monto_total} registrada para {comprador.nombre}.')
            return redirect('detalle_comprador', pk=comprador.pk)

        except Exception as e:
            messages.error(request, f'Error al registrar la venta: {str(e)}')
            
            # Recargamos los datos para el GET
            compradores_existentes = Comprador.objects.filter(activo=True).order_by('nombre')
            lotes = Lote.objects.filter(activo=True)
            procesados = Procesado.objects.all()[:50]
            mezclas = Mezcla.objects.all()[:50]
            
            context = {
                'compradores': compradores_existentes,
                'lotes': lotes,
                'procesados': procesados,
                'mezclas': mezclas,
                'form_data': request.POST
            }
            return render(request, 'beneficio/compradores/registrar_venta.html', context)
    
    # --- Lógica para GET ---
    compradores_existentes = Comprador.objects.filter(activo=True).order_by('nombre')
    # CORREGIDO: 'tipo_cafe' no es relacional
    lotes = Lote.objects.filter(activo=True)
    procesados = Procesado.objects.select_related('lote').all().order_by('-fecha')[:50]
    mezclas = Mezcla.objects.all().order_by('-fecha')[:50]
    
    context = {
        'compradores': compradores_existentes,
        'lotes': lotes,
        'procesados': procesados,
        'mezclas': mezclas,
    }
    return render(request, 'beneficio/compradores/registrar_venta.html', context)


# ==========================================
# VISTAS DE CONTROL DE MANTENIMIENTO
# ==========================================


@login_required
def control_mantenimiento(request):
    """Vista principal del control de mantenimiento de la planta"""
    control = MantenimientoPlanta.get_or_create_control()
    
    historial_reciente = HistorialMantenimiento.objects.all()[:10]
    total_mantenimientos = HistorialMantenimiento.objects.count()
    
    # Procesos recientes
    procesados_recientes = Procesado.objects.filter(
        hora_inicio__isnull=False,
        hora_final__isnull=False
    ).order_by('-fecha')[:5]
    
    reprocesos_recientes = Reproceso.objects.filter(
        hora_inicio__isnull=False,
        hora_final__isnull=False
    ).order_by('-fecha')[:5]
    
    mezclas_recientes = Mezcla.objects.filter(
        hora_inicio__isnull=False,
        hora_final__isnull=False
    ).order_by('-fecha')[:5]
    
    # Determinar nivel de alerta
    porcentaje = control.porcentaje_uso
    if porcentaje >= 100:
        nivel_alerta = 'critico'
        mensaje_alerta = '¡URGENTE! La planta requiere mantenimiento inmediato'
    elif porcentaje >= 90:
        nivel_alerta = 'advertencia'
        mensaje_alerta = '¡ADVERTENCIA! La planta está cerca de requerir mantenimiento'
    elif porcentaje >= 75:
        nivel_alerta = 'precaucion'
        mensaje_alerta = 'Atención: Programe el próximo mantenimiento pronto'
    else:
        nivel_alerta = 'normal'
        mensaje_alerta = 'La planta está operando normalmente'
    
    context = {
        'control': control,
        'historial_reciente': historial_reciente,
        'total_mantenimientos': total_mantenimientos,
        'procesados_recientes': procesados_recientes,
        'reprocesos_recientes': reprocesos_recientes,
        'mezclas_recientes': mezclas_recientes,
        'nivel_alerta': nivel_alerta,
        'mensaje_alerta': mensaje_alerta,
    }
    return render(request, 'beneficio/mantenimiento/control.html', context)


@login_required
def realizar_mantenimiento(request):
    """Registrar un mantenimiento y reiniciar el contador"""
    control = MantenimientoPlanta.get_or_create_control()
    
    if request.method == 'POST':
        try:
            tipo_mantenimiento = request.POST.get('tipo_mantenimiento', 'preventivo')
            observaciones = request.POST.get('observaciones', '')
            tiempo_mantenimiento = request.POST.get('tiempo_mantenimiento_horas', 0)
            costo = request.POST.get('costo', 0)
            
            # Crear registro de mantenimiento
            mantenimiento = HistorialMantenimiento.objects.create(
                control_mantenimiento=control,
                horas_acumuladas=control.horas_acumuladas,
                tipo_mantenimiento=tipo_mantenimiento,
                observaciones=observaciones,
                tiempo_mantenimiento_horas=tiempo_mantenimiento,
                costo=costo,
                realizado_por=request.user
            )
            
            # Reiniciar contador
            control.horas_acumuladas = 0
            control.estado = 'operativa'
            control.ultimo_mantenimiento = timezone.now()
            control.save()
            
            messages.success(request, f'Mantenimiento registrado exitosamente. Contador reiniciado a 0 horas.')
            return redirect('control_mantenimiento')
            
        except Exception as e:
            messages.error(request, f'Error al registrar mantenimiento: {str(e)}')
    
    context = {
        'control': control,
    }
    return render(request, 'beneficio/mantenimiento/realizar.html', context)


@login_required
def historial_mantenimiento(request):
    """Vista del historial completo de mantenimientos"""
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    tipo = request.GET.get('tipo')
    
    historial = HistorialMantenimiento.objects.all().order_by('-fecha_mantenimiento')
    
    if fecha_desde:
        historial = historial.filter(fecha_mantenimiento__date__gte=fecha_desde)
    if fecha_hasta:
        historial = historial.filter(fecha_mantenimiento__date__lte=fecha_hasta)
    if tipo:
        historial = historial.filter(tipo_mantenimiento=tipo)
    
    # Estadísticas
    total_mantenimientos = historial.count()
    costo_total = historial.aggregate(Sum('costo'))['costo__sum'] or 0
    tiempo_total = historial.aggregate(Sum('tiempo_mantenimiento_horas'))['tiempo_mantenimiento_horas__sum'] or 0
    
    context = {
        'historial': historial,
        'total_mantenimientos': total_mantenimientos,
        'costo_total': costo_total,
        'tiempo_total': tiempo_total,
    }
    return render(request, 'beneficio/mantenimiento/historial.html', context)

# ==========================================
# VISTAS DE RECIBOS DE CAFÉ
# ==========================================

@login_required
def agregar_recibo(request, lote_id):
    """Agregar un nuevo recibo de café a un lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                recibo = ReciboCafe()
                recibo.lote = lote
                
                fecha_recibo_str = request.POST.get('fecha_recibo')
                recibo.fecha_recibo = fecha_recibo_str if fecha_recibo_str else timezone.now()
                
                # CORREGIDO: Validar campos numéricos antes de convertir
                peso_str = request.POST.get('peso')
                humedad_str = request.POST.get('humedad')
                precio_str = request.POST.get('precio_quintal')
                
                if not peso_str or not humedad_str or not precio_str:
                    messages.error(request, 'Por favor complete todos los campos obligatorios (Peso, Humedad, Precio)')
                    return redirect('agregar_recibo', lote_id=lote.pk)
                
                try:
                    recibo.peso = Decimal(peso_str)
                    recibo.humedad = Decimal(humedad_str)
                    recibo.precio_quintal = Decimal(precio_str)
                except (ValueError, decimal.InvalidOperation):
                    messages.error(request, 'Por favor ingrese valores numéricos válidos')
                    return redirect('agregar_recibo', lote_id=lote.pk)
                
                recibo.unidad = request.POST.get('unidad', 'qq')
                recibo.proveedor = request.POST.get('proveedor', '')
                
                # Campo opcional con valor por defecto
                numero_boletas_str = request.POST.get('numero_boletas', '0')
                try:
                    recibo.numero_boletas = int(numero_boletas_str) if numero_boletas_str else 0
                except ValueError:
                    recibo.numero_boletas = 0
                
                recibo.observaciones = request.POST.get('observaciones', '')
                recibo.registrado_por = request.user
                
                recibo.save()
                
                messages.success(request, f'Recibo {recibo.numero_recibo} agregado exitosamente al Lote {lote.codigo}')
                return redirect('detalle_lote', pk=lote.pk)
                
        except Exception as e:
            messages.error(request, f'Error al agregar recibo: {str(e)}')
    
    context = {
        'lote': lote,
    }
    return render(request, 'beneficio/recibos/agregar.html', context)


@login_required
def editar_recibo(request, pk):
    """Editar un recibo existente"""
    recibo = get_object_or_404(ReciboCafe, pk=pk)
    peso_anterior_kg = recibo.convertir_a_kg()
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # CORREGIDO: Validar campos antes de convertir
                peso_str = request.POST.get('peso')
                humedad_str = request.POST.get('humedad')
                precio_str = request.POST.get('precio_quintal')
                
                if not peso_str or not humedad_str or not precio_str:
                    messages.error(request, 'Por favor complete todos los campos obligatorios')
                    return redirect('editar_recibo', pk=recibo.pk)
                
                try:
                    nuevo_peso = Decimal(peso_str)
                    nueva_humedad = Decimal(humedad_str)
                    nuevo_precio = Decimal(precio_str)
                except (ValueError, decimal.InvalidOperation):
                    messages.error(request, 'Por favor ingrese valores numéricos válidos')
                    return redirect('editar_recibo', pk=recibo.pk)
                
                nueva_unidad = request.POST.get('unidad', 'qq')
                
                recibo.peso = nuevo_peso
                recibo.unidad = nueva_unidad
                recibo.humedad = nueva_humedad
                recibo.proveedor = request.POST.get('proveedor', '')
                recibo.precio_quintal = nuevo_precio
                
                numero_boletas_str = request.POST.get('numero_boletas', '0')
                try:
                    recibo.numero_boletas = int(numero_boletas_str) if numero_boletas_str else 0
                except ValueError:
                    recibo.numero_boletas = 0
                    
                recibo.observaciones = request.POST.get('observaciones', '')
                
                # Calcular nuevo peso en kg
                nuevo_peso_kg = recibo.convertir_a_kg()
                diferencia_kg = nuevo_peso_kg - peso_anterior_kg
                
                # Actualizar peso del lote
                recibo.lote.peso_kg = Decimal(str(recibo.lote.peso_kg)) + Decimal(str(diferencia_kg))
                recibo.lote.save(update_fields=['peso_kg'])
                
                # Recalcular monto
                peso_qq = recibo.convertir_a_quintales()
                recibo.monto_total = Decimal(str(peso_qq)) * recibo.precio_quintal
                
                recibo.save()
                
                messages.success(request, f'Recibo {recibo.numero_recibo} actualizado exitosamente')
                return redirect('detalle_lote', pk=recibo.lote.pk)
                
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    context = {
        'recibo': recibo,
    }
    return render(request, 'beneficio/recibos/editar.html', context)


@login_required
def eliminar_recibo(request, pk):
    """Eliminar un recibo de café"""
    recibo = get_object_or_404(ReciboCafe, pk=pk)
    lote = recibo.lote
    
    if request.method == 'POST':
        numero = recibo.numero_recibo
        recibo.delete()
        messages.success(request, f'Recibo {numero} eliminado exitosamente')
        return redirect('detalle_lote', pk=lote.pk)
    
    context = {
        'recibo': recibo,
    }
    return render(request, 'beneficio/recibos/eliminar.html', context)

@login_required
def procesar_desde_recibo(request, recibo_id):
    """Procesar café desde un recibo específico"""
    recibo = get_object_or_404(ReciboCafe, pk=recibo_id)
    lote = recibo.lote
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                procesado = Procesado()
                procesado.lote = lote
                procesado.recibo = recibo  # Vincular con el recibo
                
                # Horario
                hora_inicio_str = request.POST.get('hora_inicio')
                if hora_inicio_str:
                    procesado.hora_inicio = hora_inicio_str
                
                hora_final_str = request.POST.get('hora_final')
                if hora_final_str:
                    procesado.hora_final = hora_final_str
                
                # Validar peso
                peso_a_procesar = Decimal(request.POST.get('peso_inicial_kg', '0'))
                
                # Calcular peso disponible en kg
                if recibo.unidad == 'qq':
                    peso_disponible_kg = Decimal(str(recibo.peso_disponible)) * Decimal('46')
                elif recibo.unidad == 'lb':
                    peso_disponible_kg = Decimal(str(recibo.peso_disponible)) * Decimal('0.453592')
                else:  # kg
                    peso_disponible_kg = Decimal(str(recibo.peso_disponible))
                
                if peso_a_procesar > peso_disponible_kg:
                    messages.error(
                        request, 
                        f'No puedes procesar más de {peso_disponible_kg:.2f} kg disponibles en el recibo {recibo.numero_recibo}'
                    )
                    return redirect('procesar_desde_recibo', recibo_id=recibo.pk)
                
                # Pesos
                procesado.peso_inicial_kg = peso_a_procesar
                procesado.unidad_peso_inicial = request.POST.get('unidad_peso_inicial', 'kg')
                procesado.peso_final_kg = request.POST.get('peso_final_kg', '0')
                procesado.unidad_peso_final = request.POST.get('unidad_peso_final', 'kg')
                
                # Clasificación
                procesado.cafe_primera = request.POST.get('cafe_primera', 0)
                procesado.unidad_cafe_primera = request.POST.get('unidad_cafe_primera', 'kg')
                procesado.cafe_segunda = request.POST.get('cafe_segunda', 0)
                procesado.unidad_cafe_segunda = request.POST.get('unidad_cafe_segunda', 'kg')
                
                # Mermas
                procesado.catadura = request.POST.get('catadura', 0)
                procesado.rechazo_electronica = request.POST.get('rechazo_electronica', 0)
                procesado.bajo_zaranda = request.POST.get('bajo_zaranda', 0)
                procesado.barridos = request.POST.get('barridos', 0)
                
                procesado.observaciones = request.POST.get('observaciones', '')
                procesado.operador = request.user
                
                # Guardar el procesado (el número de trilla se genera automáticamente)
                procesado.save()
                
                # Registrar el peso procesado en el recibo
                # Convertir peso_a_procesar a la unidad del recibo
                if recibo.unidad == 'qq':
                    cantidad_procesada_en_unidad_recibo = peso_a_procesar / Decimal('46')
                elif recibo.unidad == 'lb':
                    cantidad_procesada_en_unidad_recibo = peso_a_procesar / Decimal('0.453592')
                else:  # kg
                    cantidad_procesada_en_unidad_recibo = peso_a_procesar
                
                recibo.registrar_procesamiento(cantidad_procesada_en_unidad_recibo)
                
                messages.success(
                    request, 
                    f'✅ Trilla {procesado.numero_trilla} creada exitosamente desde el recibo {recibo.numero_recibo}'
                )
                return redirect('detalle_procesado', pk=procesado.id)
                
        except Exception as e:
            messages.error(request, f'Error al crear procesado: {str(e)}')
            import traceback
            print(traceback.format_exc())  
    
    # Calcular peso sugerido (todo el peso disponible del recibo en kg)
    if recibo.unidad == 'qq':
        peso_sugerido_kg = float(recibo.peso_disponible) * 46
    elif recibo.unidad == 'lb':
        peso_sugerido_kg = float(recibo.peso_disponible) * 0.453592
    else:  # kg
        peso_sugerido_kg = float(recibo.peso_disponible)
    
    context = {
        'recibo': recibo,
        'lote': lote,
        'peso_sugerido_kg': peso_sugerido_kg,
    }
    return render(request, 'beneficio/recibos/procesar.html', context)

@login_required
def editar_mezcla(request, pk):
    """Editar una mezcla completa con sus componentes"""
    mezcla = get_object_or_404(Mezcla, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Actualizar información básica
                mezcla.destino = request.POST.get('destino')
                mezcla.descripcion = request.POST.get('descripcion', '')
                mezcla.fecha = request.POST.get('fecha')
                
                # Bodega de almacenamiento
                bodega_id = request.POST.get('bodega_destino')
                if bodega_id:
                    mezcla.bodega_destino_id = bodega_id
                
                # Batchadas por día (nuevo campo)
                batchadas = request.POST.get('batchadas_dia', '1')
                try:
                    # Si tienes este campo en tu modelo, descomenta:
                    # mezcla.batchadas_dia = int(batchadas)
                    pass
                except:
                    pass
                
                # ELIMINAR TODOS LOS COMPONENTES EXISTENTES
                mezcla.detalles.all().delete()
                
                # AGREGAR NUEVOS COMPONENTES
                componentes = json.loads(request.POST.get('componentes', '[]'))
                
                if not componentes:
                    raise Exception("Debe agregar al menos un componente a la mezcla")
                
                peso_total = Decimal('0')
                
                for comp in componentes:
                    lote = get_object_or_404(Lote, pk=comp['lote_id'])
                    peso = Decimal(str(comp['peso']))
                    
                    DetalleMezcla.objects.create(
                        mezcla=mezcla,
                        lote=lote,
                        peso_kg=peso,
                        porcentaje=0  # Se recalculará después
                    )
                    
                    peso_total += peso
                
                # Actualizar peso total de la mezcla
                mezcla.peso_total_kg = peso_total
                
                # Recalcular porcentajes
                if peso_total > 0:
                    for detalle in mezcla.detalles.all():
                        detalle.porcentaje = (Decimal(str(detalle.peso_kg)) / peso_total) * 100
                        detalle.save()
                
                mezcla.save()
                
                messages.success(request, f'✅ Mezcla #{mezcla.numero} actualizada exitosamente')
                return redirect('detalle_mezcla', pk=mezcla.pk)
                
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar: {str(e)}')
    
    # GET - Preparar datos para el formulario
    
    # Componentes existentes
    componentes_existentes = []
    for detalle in mezcla.detalles.all():
        componentes_existentes.append({
            'lote_id': detalle.lote.id,
            'peso': float(detalle.peso_kg),
            'porcentaje': float(detalle.porcentaje)
        })
    
    # Opciones para componentes
    opciones_mezcla = []
    
    # 1. LOTES
    for lote in Lote.objects.filter(activo=True):
        opciones_mezcla.append({
            'lote_id': lote.id,
            'tipo': '📦 Lote',
            'codigo': lote.codigo,
            'descripcion': f"{lote.tipo_cafe} - Bodega {lote.bodega.codigo}",
            'peso_disponible': float(lote.peso_kg)
        })
    
    # 2. PROCESADOS
    for procesado in Procesado.objects.select_related('lote').all()[:50]:
        opciones_mezcla.append({
            'lote_id': procesado.lote.id,
            'tipo': '⚙️ Procesado',
            'codigo': f"Trilla #{procesado.numero_trilla}",
            'descripcion': f"Lote {procesado.lote.codigo} - {procesado.lote.tipo_cafe}",
            'peso_disponible': float(procesado.peso_final_kg)
        })
    
    # 3. REPROCESOS
    for reproceso in Reproceso.objects.select_related('procesado__lote').all()[:50]:
        nombre = reproceso.nombre if reproceso.nombre else f"Reproceso #{reproceso.numero}"
        opciones_mezcla.append({
            'lote_id': reproceso.procesado.lote.id,
            'tipo': '🔄 Reproceso',
            'codigo': nombre,
            'descripcion': f"Lote {reproceso.procesado.lote.codigo} - De Trilla #{reproceso.procesado.numero_trilla}",
            'peso_disponible': float(reproceso.peso_final_kg)
        })
    
    context = {
        'mezcla': mezcla,
        'bodegas': Bodega.objects.all(),
        'opciones_json': json.dumps(opciones_mezcla),
        'componentes_existentes': json.dumps(componentes_existentes),
    }
    return render(request, 'beneficio/mezclas/editar.html', context)

@login_required
def continuar_mezcla(request, mezcla_id):
    """Vista para continuar/agregar más componentes a una mezcla existente"""
    mezcla = get_object_or_404(Mezcla, id=mezcla_id)
    
    # Obtener componentes actuales de la mezcla
    detalles_actuales = mezcla.detalles.all()
    
    # Obtener lotes disponibles (excluyendo los que ya están en la mezcla)
    lotes_en_mezcla = [d.lote.id for d in detalles_actuales]
    lotes_disponibles = Lote.objects.filter(activo=True).exclude(id__in=lotes_en_mezcla)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Actualizar información básica de la mezcla si se proporcionó
                descripcion_nueva = request.POST.get('descripcion')
                if descripcion_nueva:
                    mezcla.descripcion = descripcion_nueva
                
                destino_nuevo = request.POST.get('destino')
                if destino_nuevo:
                    mezcla.destino = destino_nuevo
                
                # Actualizar horarios si se proporcionaron
                hora_inicio_str = request.POST.get('hora_inicio')
                hora_final_str = request.POST.get('hora_final')
                
                if hora_inicio_str:
                    mezcla.hora_inicio = hora_inicio_str
                if hora_final_str:
                    mezcla.hora_final = hora_final_str
                
                # Actualizar bodega de destino
                bodega_id = request.POST.get('bodega_destino')
                if bodega_id:
                    mezcla.bodega_destino = Bodega.objects.get(id=bodega_id)
                
                # Procesar nuevos componentes
                lotes_ids = request.POST.getlist('lotes[]')
                pesos = request.POST.getlist('pesos[]')
                
                peso_total_nuevo = Decimal('0')
                
                for lote_id, peso in zip(lotes_ids, pesos):
                    if lote_id and peso:
                        lote = Lote.objects.get(id=lote_id)
                        peso_decimal = Decimal(peso)
                        
                        # Crear nuevo detalle de mezcla
                        DetalleMezcla.objects.create(
                            mezcla=mezcla,
                            lote=lote,
                            peso_kg=peso_decimal,
                            porcentaje=0  # Se calculará después
                        )
                        
                        peso_total_nuevo += peso_decimal
                
                # Recalcular peso total y porcentajes
                peso_total_mezcla = sum(d.peso_kg for d in mezcla.detalles.all())
                mezcla.peso_total_kg = peso_total_mezcla
                
                # Actualizar porcentajes de TODOS los componentes
                for detalle in mezcla.detalles.all():
                    if peso_total_mezcla > 0:
                        detalle.porcentaje = (detalle.peso_kg / peso_total_mezcla) * 100
                        detalle.save()
                
                mezcla.save()
                
                messages.success(request, f'Mezcla #{mezcla.numero} actualizada exitosamente. Se agregaron {len(lotes_ids)} nuevos componentes.')
                return redirect('detalle_mezcla', mezcla_id=mezcla.id)
                
        except Exception as e:
            messages.error(request, f'Error al continuar la mezcla: {str(e)}')
    
    # Calcular peso actual de la mezcla
    peso_actual = sum(d.peso_kg for d in detalles_actuales)
    
    context = {
        'mezcla': mezcla,
        'detalles_actuales': detalles_actuales,
        'peso_actual': peso_actual,
        'lotes_disponibles': lotes_disponibles,
        'bodegas': Bodega.objects.all(),
    }
    
    return render(request, 'beneficio/mezclas/continuar.html', context)

@login_required
def eventos_lista(request):
    """Vista principal de eventos - muestra todos los productos disponibles"""
    
    # Filtros
    tipo_filtro = request.GET.get('tipo', 'todos')
    estado_filtro = request.GET.get('estado', 'todos')
    
    # Obtener productos
    procesados = list(Procesado.objects.all().select_related('lote'))
    reprocesos = list(Reproceso.objects.all())
    mezclas = list(Mezcla.objects.all())
    
    # Aplicar filtros de estado
    if estado_filtro == 'disponible':
        procesados = [p for p in procesados if not p.esta_vendido and not p.esta_exportado]
        reprocesos = [r for r in reprocesos if not r.esta_vendido and not r.esta_exportado]
        mezclas = [m for m in mezclas if not m.esta_vendida and not m.esta_exportada]
    elif estado_filtro == 'vendido':
        procesados = [p for p in procesados if p.esta_vendido]
        reprocesos = [r for r in reprocesos if r.esta_vendido]
        mezclas = [m for m in mezclas if m.esta_vendida]
    elif estado_filtro == 'exportado':
        procesados = [p for p in procesados if p.esta_exportado]
        reprocesos = [r for r in reprocesos if r.esta_exportado]
        mezclas = [m for m in mezclas if m.esta_exportada]
    
    # Crear lista unificada
    productos = []
    
    # Procesados
    if tipo_filtro in ['todos', 'procesado']:
        for p in procesados:
            try:
                peso_disp = float(p.peso_disponible)
            except (TypeError, ValueError, AttributeError):
                peso_disp = 0.0
            
            try:
                fecha = p.fecha
            except AttributeError:
                fecha = getattr(p, 'fecha_procesamiento', getattr(p, 'created_at', None))
            
            lote_codigo = 'N/A'
            if hasattr(p, 'lote') and p.lote:
                lote_codigo = getattr(p.lote, 'codigo', f"LOTE-{p.lote.id}")
            
            productos.append({
                'tipo': 'procesado',
                'id': p.id,
                'codigo': f"PROC-{p.id}",
                'descripcion': f"Lote {lote_codigo}",
                'peso_disponible': peso_disp,
                'fecha': fecha,
                'esta_vendido': p.esta_vendido,
                'esta_exportado': p.esta_exportado,
                'objeto': p
            })
    
    # Reprocesos
    if tipo_filtro in ['todos', 'reproceso']:
        for r in reprocesos:
            try:
                peso_disp = float(r.peso_disponible)
            except (TypeError, ValueError, AttributeError):
                peso_disp = 0.0
            
            try:
                fecha = r.fecha
            except AttributeError:
                fecha = getattr(r, 'fecha_reproceso', getattr(r, 'created_at', None))
            
            origen = 'N/A'
            if hasattr(r, 'procesado_origen') and r.procesado_origen:
                origen = getattr(r.procesado_origen, 'codigo', f"PROC-{r.procesado_origen.id}")
            
            productos.append({
                'tipo': 'reproceso',
                'id': r.id,
                'codigo': f"REP-{r.id}",
                'descripcion': f"Origen: {origen}",
                'peso_disponible': peso_disp,
                'fecha': fecha,
                'esta_vendido': r.esta_vendido,
                'esta_exportado': r.esta_exportado,
                'objeto': r
            })
    
    # Mezclas
    if tipo_filtro in ['todos', 'mezcla']:
        for m in mezclas:
            try:
                peso_disp = float(m.peso_disponible)
            except (TypeError, ValueError, AttributeError):
                peso_disp = 0.0
            
            try:
                fecha = m.fecha_mezcla
            except AttributeError:
                fecha = getattr(m, 'fecha_creacion', getattr(m, 'fecha', getattr(m, 'created_at', None)))
            
            codigo = getattr(m, 'codigo', f"MIX-{m.id}")
            nombre = getattr(m, 'nombre', f"Mezcla {m.id}")
            
            productos.append({
                'tipo': 'mezcla',
                'id': m.id,
                'codigo': codigo,
                'descripcion': nombre,
                'peso_disponible': peso_disp,
                'fecha': fecha,
                'esta_vendido': m.esta_vendida,
                'esta_exportado': m.esta_exportada,
                'objeto': m
            })
    
    # Ordenar por fecha
    productos.sort(key=lambda x: x['fecha'] if x['fecha'] else '', reverse=True)
    
    # Estadísticas
    total_productos = len(productos)
    total_disponible = sum([p['peso_disponible'] for p in productos if not p['esta_vendido'] and not p['esta_exportado']])
    
    # Totales vendidos y exportados
    total_vendido_agg = Venta.objects.filter(estado='completada').aggregate(Sum('peso_vendido_kg'))['peso_vendido_kg__sum']
    total_vendido = float(total_vendido_agg) if total_vendido_agg else 0.0
    
    total_exportado_agg = Exportacion.objects.filter(estado='entregada').aggregate(Sum('peso_exportado_kg'))['peso_exportado_kg__sum']
    total_exportado = float(total_exportado_agg) if total_exportado_agg else 0.0
    
    context = {
        'productos': productos,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
        'total_productos': total_productos,
        'total_disponible': total_disponible,
        'total_vendido': total_vendido,
        'total_exportado': total_exportado,
    }
    
    return render(request, 'beneficio/eventos/lista.html', context)

# ============================================================================
# VENTAS
# ============================================================================

@login_required
def venta_crear(request, tipo_producto, producto_id):
    """
    Crear nueva venta desde un procesado, reproceso o mezcla
    
    tipo_producto: 'procesado', 'reproceso' o 'mezcla'
    producto_id: ID del producto a vender
    """
    
    # Obtener el producto según el tipo
    producto = None
    nombre_tipo = ""
    peso_disponible_kg = Decimal('0')
    
    if tipo_producto == 'procesado':
        producto = get_object_or_404(Procesado, pk=producto_id)
        nombre_tipo = f"Procesado {producto.numero_trilla}"
        peso_disponible_kg = Decimal(str(producto.peso_final_kg))
    elif tipo_producto == 'reproceso':
        producto = get_object_or_404(Reproceso, pk=producto_id)
        nombre_tipo = f"Reproceso {producto.numero}"
        peso_disponible_kg = Decimal(str(producto.peso_final_kg))
    elif tipo_producto == 'mezcla':
        producto = get_object_or_404(Mezcla, pk=producto_id)
        nombre_tipo = f"Mezcla {producto.numero}"
        peso_disponible_kg = Decimal(str(producto.peso_total_kg))
    else:
        messages.error(request, '❌ Tipo de producto inválido')
        return redirect('eventos_lista')
    
    if request.method == 'POST':
        try:
            # PASO 1: Obtener datos del formulario
            unidad_medida = request.POST.get('unidad_medida', '').strip()
            cantidad_str = request.POST.get('cantidad', '').strip()
            peso_por_unidad_str = request.POST.get('peso_por_unidad', '1').strip()
            precio_quintal_str = request.POST.get('precio_quintal', '').strip()
            
            print(f"📥 DATOS RECIBIDOS:")
            print(f"   Tipo producto: {tipo_producto}")
            print(f"   Producto ID: {producto_id}")
            print(f"   Unidad: {unidad_medida}")
            print(f"   Cantidad: {cantidad_str}")
            print(f"   Peso por unidad: {peso_por_unidad_str}")
            print(f"   Precio: {precio_quintal_str}")
            
            # PASO 2: Validar campos obligatorios
            if not unidad_medida:
                messages.error(request, '❌ Debes seleccionar una unidad de medida')
                return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
            
            if not cantidad_str:
                messages.error(request, '❌ Debes ingresar una cantidad')
                return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
            
            if not precio_quintal_str:
                messages.error(request, '❌ Debes ingresar el precio por quintal')
                return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
            
            # PASO 3: Convertir a Decimal
            try:
                cantidad = Decimal(cantidad_str)
                peso_por_unidad = Decimal(peso_por_unidad_str)
                precio_quintal = Decimal(precio_quintal_str)
            except (ValueError, InvalidOperation) as e:
                messages.error(request, f'❌ Error en los números ingresados: {str(e)}')
                return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
            
            # PASO 4: Calcular peso en kilogramos
            factores_conversion = {
                'kg': Decimal('1'),
                'gramos': Decimal('0.001'),
                'libras': Decimal('0.453592'),
                'quintales': Decimal('45.36'),
                'bolsas': Decimal('0.453592'),
                'sacos': Decimal('46'),
            }
            
            if unidad_medida not in factores_conversion:
                messages.error(request, f'❌ Unidad de medida inválida: {unidad_medida}')
                return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
            
            # Calcular peso en kg
            if unidad_medida == 'bolsas':
                peso_vendido_kg = cantidad * peso_por_unidad * factores_conversion['libras']
                print(f"   Cálculo bolsas: {cantidad} × {peso_por_unidad} lb × {factores_conversion['libras']} = {peso_vendido_kg} kg")
            else:
                peso_vendido_kg = cantidad * factores_conversion[unidad_medida]
                print(f"   Cálculo {unidad_medida}: {cantidad} × {factores_conversion[unidad_medida]} = {peso_vendido_kg} kg")
            
            print(f"✅ Peso calculado: {peso_vendido_kg} kg")
            
            # PASO 5: Validar que no sea cero
            if peso_vendido_kg <= 0:
                messages.error(request, '❌ El peso a vender debe ser mayor a 0')
                return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
            
            # PASO 6: Validar que no exceda el disponible
            if peso_vendido_kg > peso_disponible_kg:
                messages.error(
                    request,
                    f'❌ El peso a vender ({peso_vendido_kg:.2f} kg) excede el disponible ({peso_disponible_kg:.2f} kg)'
                )
                return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
            
            # PASO 7: Calcular precio total
            quintales = peso_vendido_kg / Decimal('45.36')
            precio_total = quintales * precio_quintal
            
            print(f"💰 Cálculo precio:")
            print(f"   Quintales: {quintales:.4f} qq")
            print(f"   Precio/qq: Q {precio_quintal}")
            print(f"   Total: Q {precio_total:.2f}")
            
            # PASO 8: Crear la venta
            with transaction.atomic():
                venta_data = {
                    'tipo_producto': tipo_producto,
                    'unidad_medida': unidad_medida,
                    'cantidad': cantidad,
                    'peso_por_unidad': peso_por_unidad if unidad_medida == 'bolsas' else None,
                    'peso_vendido_kg': peso_vendido_kg,
                    'precio_quintal': precio_quintal,
                    'precio_total': precio_total,
                    'comprador_id': request.POST.get('comprador') or None,
                    'estado': request.POST.get('estado', 'completada'),
                    'numero_factura': request.POST.get('numero_factura', ''),
                    'numero_contrato': request.POST.get('numero_contrato', ''),
                    'fecha_entrega': request.POST.get('fecha_entrega') or None,
                    'transportista': request.POST.get('transportista', ''),
                    'numero_placa': request.POST.get('numero_placa', ''),
                    'observaciones': request.POST.get('observaciones', ''),
                    'creado_por': request.user,
                }
                
                # Asignar el producto según el tipo
                if tipo_producto == 'procesado':
                    venta_data['procesado'] = producto
                elif tipo_producto == 'reproceso':
                    venta_data['reproceso'] = producto
                elif tipo_producto == 'mezcla':
                    venta_data['mezcla'] = producto
                
                venta = Venta.objects.create(**venta_data)
                
                # PASO 9: Restar del producto
                if tipo_producto == 'procesado':
                    producto.peso_final_kg = Decimal(str(producto.peso_final_kg)) - peso_vendido_kg
                    producto.save(update_fields=['peso_final_kg'])
                elif tipo_producto == 'reproceso':
                    producto.peso_final_kg = Decimal(str(producto.peso_final_kg)) - peso_vendido_kg
                    producto.save(update_fields=['peso_final_kg'])
                elif tipo_producto == 'mezcla':
                    producto.peso_total_kg = Decimal(str(producto.peso_total_kg)) - peso_vendido_kg
                    producto.save(update_fields=['peso_total_kg'])
                
                print(f"✅ Venta creada: {venta.codigo_venta}")
                print(f"✅ Peso restado del {tipo_producto}: {peso_disponible_kg} - {peso_vendido_kg} = {peso_disponible_kg - peso_vendido_kg} kg")
            
            messages.success(
                request,
                f'✅ Venta registrada exitosamente<br>'
                f'📦 Vendido: {cantidad} {unidad_medida} = {peso_vendido_kg:.2f} kg<br>'
                f'💰 Total: Q {precio_total:,.2f}'
            )
            return redirect('eventos_lista')
            
        except Exception as e:
            messages.error(request, f'❌ Error al crear venta: {str(e)}')
            import traceback
            print("❌ ERROR COMPLETO:")
            print(traceback.format_exc())
            return redirect('venta_crear', tipo_producto=tipo_producto, producto_id=producto_id)
    
    # GET - Mostrar formulario
    compradores = Comprador.objects.filter(activo=True)
    
    context = {
        'tipo_producto': tipo_producto,
        'producto': producto,
        'nombre_tipo': nombre_tipo,
        'peso_disponible': peso_disponible_kg,
        'compradores': compradores,
    }
    return render(request, 'beneficio/eventos/venta_crear.html', context)

@login_required
def venta_detalle(request, venta_id):
    """Ver detalles de una venta"""
    venta = get_object_or_404(Venta, id=venta_id)
    
    context = {
        'venta': venta,
    }
    
    return render(request, 'beneficio/eventos/venta_detalle.html', context)


@login_required
def ventas_lista(request):
    """Listar todas las ventas"""
    ventas = Venta.objects.all().select_related('comprador', 'procesado', 'reproceso', 'mezcla', 'creado_por')
    
    # Filtros
    estado = request.GET.get('estado')
    if estado:
        ventas = ventas.filter(estado=estado)
    
    context = {
        'ventas': ventas,
    }
    
    return render(request, 'beneficio/eventos/ventas_lista.html', context)


# ============================================================================
# EXPORTACIONES
# ============================================================================

@login_required
def exportacion_crear(request, tipo_producto, producto_id):
    """
    Vista para crear una nueva exportación
    Soporta múltiples unidades de medida: kg, gramos, libras, quintales, bolsas, sacos
    """
    
    # Obtener el producto según el tipo
    if tipo_producto == 'procesado':
        producto = get_object_or_404(Procesado, id=producto_id)
        nombre_tipo = 'Procesado'
    elif tipo_producto == 'reproceso':
        producto = get_object_or_404(Reproceso, id=producto_id)
        nombre_tipo = 'Reproceso'
    elif tipo_producto == 'mezcla':
        producto = get_object_or_404(Mezcla, id=producto_id)
        nombre_tipo = 'Mezcla'
    else:
        messages.error(request, 'Tipo de producto no válido')
        return redirect('eventos_lista')
    
    # Verificar que haya peso disponible
    try:
        peso_disponible_kg = Decimal(str(producto.peso_disponible))
    except (TypeError, ValueError, AttributeError):
        peso_disponible_kg = Decimal('0')
    
    if peso_disponible_kg <= 0:
        messages.error(request, f'No hay peso disponible para exportar en este {nombre_tipo}')
        return redirect('eventos_lista')
    
    # Obtener compradores activos
    compradores = Comprador.objects.filter(activo=True)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # PASO 1: Obtener datos del formulario
                unidad_medida = request.POST.get('unidad_medida', '').strip()
                cantidad_str = request.POST.get('cantidad', '').strip()
                peso_por_unidad_str = request.POST.get('peso_por_unidad', '1').strip()
                precio_quintal_str = request.POST.get('precio_quintal', '').strip()
                
                print(f"📥 DATOS RECIBIDOS:")
                print(f"   Tipo producto: {tipo_producto}")
                print(f"   Producto ID: {producto_id}")
                print(f"   Unidad: {unidad_medida}")
                print(f"   Cantidad: {cantidad_str}")
                print(f"   Peso por unidad: {peso_por_unidad_str}")
                print(f"   Precio: {precio_quintal_str}")
                
                # PASO 2: Validar campos obligatorios
                if not unidad_medida:
                    messages.error(request, '❌ Debes seleccionar una unidad de medida')
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                if not cantidad_str:
                    messages.error(request, '❌ Debes ingresar una cantidad')
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                if not precio_quintal_str:
                    messages.error(request, '❌ Debes ingresar el precio por quintal')
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                # PASO 3: Convertir a Decimal
                try:
                    cantidad = Decimal(cantidad_str)
                    peso_por_unidad = Decimal(peso_por_unidad_str)
                    precio_quintal = Decimal(precio_quintal_str)
                except (ValueError, InvalidOperation) as e:
                    messages.error(request, f'❌ Error en los números ingresados: {str(e)}')
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                # PASO 4: Calcular peso en kilogramos
                factores_conversion = {
                    'kg': Decimal('1'),
                    'gramos': Decimal('0.001'),
                    'libras': Decimal('0.453592'),
                    'quintales': Decimal('45.36'),
                    'bolsas': Decimal('0.453592'),
                    'sacos': Decimal('46'),
                }
                
                if unidad_medida not in factores_conversion:
                    messages.error(request, f'❌ Unidad de medida inválida: {unidad_medida}')
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                # Calcular peso en kg
                if unidad_medida == 'bolsas':
                  peso_exportado_kg = cantidad * peso_por_unidad * factores_conversion['libras']
                else:
                    peso_exportado_kg = cantidad * factores_conversion[unidad_medida]
                    peso_exportado_kg = Decimal(str(peso_exportado_kg))
                
                # PASO 5: Validar que no sea cero
                if peso_exportado_kg <= 0:
                    messages.error(request, '❌ El peso a exportar debe ser mayor a 0')
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                # PASO 6: Validar que no exceda el disponible
                if peso_exportado_kg > peso_disponible_kg:
                    messages.error(
                        request,
                        f'❌ El peso a exportar ({peso_exportado_kg:.2f} kg) excede el disponible ({peso_disponible_kg:.2f} kg)'
                    )
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                # PASO 7: Obtener datos adicionales
                comprador_id = request.POST.get('comprador')
                pais_destino = request.POST.get('pais_destino', '').strip()
                ciudad_destino = request.POST.get('ciudad_destino', '').strip()
                
                # Validar país destino (obligatorio)
                if not pais_destino:
                    messages.error(request, 'El país de destino es obligatorio')
                    return redirect('exportacion_crear', tipo_producto=tipo_producto, producto_id=producto_id)
                
                # Documentación
                numero_contenedor = request.POST.get('numero_contenedor', '').strip()
                numero_bl = request.POST.get('numero_bl', '').strip()
                numero_factura = request.POST.get('numero_factura', '').strip()
                certificado_origen = request.POST.get('certificado_origen', '').strip()
                
                # Logística
                tipo_envio = request.POST.get('tipo_envio', 'maritimo')
                naviera_transportista = request.POST.get('naviera_transportista', '').strip()
                fecha_embarque = request.POST.get('fecha_embarque') or None
                fecha_arribo_estimada = request.POST.get('fecha_arribo_estimada') or None
                puerto_embarque = request.POST.get('puerto_embarque', '').strip()
                puerto_destino = request.POST.get('puerto_destino', '').strip()
                
                observaciones = request.POST.get('observaciones', '').strip()
                estado = request.POST.get('estado', 'preparacion')
                
                # Obtener comprador
                comprador = None
                if comprador_id:
                    comprador = Comprador.objects.get(id=comprador_id)
                
                # Calcular precio total
                quintales = Decimal(str(peso_exportado_kg)) / Decimal('45.36')
                precio_total = quintales * precio_quintal
                
                print(f"💰 Cálculo precio:")
                print(f"   Quintales: {quintales:.4f} qq")
                print(f"   Precio/qq: Q {precio_quintal}")
                print(f"   Total: Q {precio_total:.2f}")
                
                # PASO 8: Crear la exportación
                exportacion_data = {
                    'tipo_producto': tipo_producto,
                    'unidad_medida': unidad_medida,
                    'cantidad': cantidad,
                    'peso_por_unidad': peso_por_unidad if unidad_medida == 'bolsas' else None,
                    'comprador': comprador,
                    'pais_destino': pais_destino,
                    'ciudad_destino': ciudad_destino,
                    'peso_exportado_kg': peso_exportado_kg,
                    'precio_quintal': precio_quintal,
                    'precio_total': precio_total,
                    'numero_contenedor': numero_contenedor,
                    'numero_bl': numero_bl,
                    'numero_factura': numero_factura,
                    'certificado_origen': certificado_origen,
                    'tipo_envio': tipo_envio,
                    'naviera_transportista': naviera_transportista,
                    'fecha_embarque': fecha_embarque,
                    'fecha_arribo_estimada': fecha_arribo_estimada,
                    'puerto_embarque': puerto_embarque,
                    'puerto_destino': puerto_destino,
                    'observaciones': observaciones,
                    'estado': estado,
                    'creado_por': request.user,
                }
                
                # Asignar el producto correspondiente
                if tipo_producto == 'procesado':
                    exportacion_data['procesado'] = producto
                elif tipo_producto == 'reproceso':
                    exportacion_data['reproceso'] = producto
                elif tipo_producto == 'mezcla':
                    exportacion_data['mezcla'] = producto
                
                exportacion = Exportacion.objects.create(**exportacion_data)
                
                print(f"✅ Exportación creada: {exportacion.codigo_exportacion}")
                
                # Mensaje de éxito
                messages.success(
                    request,
                    f'✅ Exportación registrada exitosamente<br>'
                    f'📦 Exportado: {cantidad} {unidad_medida} = {peso_exportado_kg:.2f} kg<br>'
                    f'✈️ Destino: {pais_destino}<br>'
                    f'💰 Total: Q {precio_total:,.2f}'
                )
                
                return redirect('eventos_lista')
        
        except Comprador.DoesNotExist:
            messages.error(request, 'El comprador seleccionado no existe')
        except ValueError as e:
            messages.error(request, f'Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al crear la exportación: {str(e)}')
            import traceback
            print("❌ ERROR COMPLETO:")
            print(traceback.format_exc())
    
    # GET request - mostrar formulario
    context = {
        'producto': producto,
        'tipo_producto': tipo_producto,
        'nombre_tipo': nombre_tipo,
        'peso_disponible': peso_disponible_kg,
        'compradores': compradores,
    }
    
    return render(request, 'beneficio/eventos/exportacion_crear.html', context)

@login_required
def exportacion_detalle(request, exportacion_id):
    """Ver detalles de una exportación"""
    exportacion = get_object_or_404(Exportacion, id=exportacion_id)
    
    context = {
        'exportacion': exportacion,
    }
    
    return render(request, 'beneficio/eventos/exportacion_detalle.html', context)


@login_required
def exportaciones_lista(request):
    """Listar todas las exportaciones"""
    exportaciones = Exportacion.objects.all().select_related('comprador', 'procesado', 'reproceso', 'mezcla', 'creado_por')
    
    # Filtros
    estado = request.GET.get('estado')
    if estado:
        exportaciones = exportaciones.filter(estado=estado)
    
    context = {
        'exportaciones': exportaciones,
    }
    
    return render(request, 'beneficio/eventos/exportaciones_lista.html', context)

@login_required
def resumen_beneficio(request):
    """Vista del resumen completo del beneficio"""
    from datetime import timedelta
    from django.utils import timezone
    
    # Últimos 30 días
    fecha_inicio = timezone.now().date() - timedelta(days=30)
    
    # Datos de Procesados
    procesados = Procesado.objects.filter(fecha__date__gte=fecha_inicio)
    reprocesos = Reproceso.objects.filter(fecha__date__gte=fecha_inicio)
    mezclas = Mezcla.objects.filter(fecha__date__gte=fecha_inicio)
    
    # Estadísticas
    stats = {
        'total_procesado': sum(p.peso_inicial_kg for p in procesados) or 0,
        'total_reproceso': sum(r.peso_inicial_kg for r in reprocesos) or 0,
        'total_mezclas': sum(m.peso_total_kg for m in mezclas) or 0,
        'variacion_procesado': 5.2,  # Puedes calcular esto comparando períodos
        'variacion_reproceso': -2.1,
        'variacion_mezclas': 3.8,
        'rendimiento_promedio': 81.5,
        'defectos_procesados_total': 0,
        'tasa_defectos_procesados': 0.0,
        'defectos_reprocesos_total': 0,
        'tasa_defectos_reprocesos': 0.0,
        'rendimiento_promedio_procesados': 81.5,
        'rendimiento_max_procesados': 95.0,
        'rendimiento_min_procesados': 65.0,
        'rendimiento_promedio_reprocesos': 78.2,
        'rendimiento_max_reprocesos': 90.0,
        'rendimiento_min_reprocesos': 60.0,
        'total_mezclas_count': mezclas.count(),
        'peso_promedio_mezclas': (sum(m.peso_total_kg for m in mezclas) / mezclas.count()) if mezclas.exists() else 0,
        'mezclas_premium': 5,
        'mezclas_estandar': 8,
        'mezclas_comercial': 3,
    }
    
    context = {
        'stats': stats,
        'procesados': procesados,
        'reprocesos': reprocesos,
        'mezclas': mezclas,
        'defectos_procesados_data': [12, 8, 5, 3, 2],  # Datos de ejemplo
        'rendimiento_procesados_labels': ['Trilla 1', 'Trilla 2', 'Trilla 3'],
        'rendimiento_procesados_data': [85, 82, 79],
        'defectos_reprocesos_data': [8, 5, 3, 2, 1],
        'rendimiento_reprocesos_labels': ['Rep 1', 'Rep 2', 'Rep 3'],
        'rendimiento_reprocesos_data': [80, 75, 82],
        'distribucion_mezclas_labels': ['Destino A', 'Destino B', 'Destino C'],
        'distribucion_mezclas_data': [40, 35, 25],
    }
    
    return render(request, 'beneficio/resumen/resumen_beneficio.html', context)

@login_required
def lista_partidas(request):
    """Lista todas las partidas con filtros"""
    # Obtener filtros
    buscar = request.GET.get('buscar', '').strip()
    activo = request.GET.get('activo')

    # Query base con campos correctos del modelo Partida
    partidas = Partida.objects.select_related(
        'bodega',
        'creado_por'
    ).all()

    # Aplicar filtros
    if buscar:
        partidas = partidas.filter(
            Q(numero_partida__icontains=buscar) |
            Q(nombre__icontains=buscar)
        )

    if activo:
        partidas = partidas.filter(activo=(activo == 'true'))
    else:
        partidas = partidas.filter(activo=True)

    partidas = partidas.order_by('-fecha_creacion')

    # Contexto
    context = {
        'partidas': partidas,
        'total_partidas': partidas.count(),
        'peso_total': partidas.aggregate(Sum('peso_total_kg'))['peso_total_kg__sum'] or 0,
    }

    return render(request, 'beneficio/partidas/lista.html', context)


# ==========================================
# CREAR PARTIDA
# ==========================================

@login_required
def crear_partida(request):
    bodegas = Bodega.objects.all()
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                partida = Partida()
                
                # Nombre (obligatorio)
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError("El nombre es obligatorio")
                partida.nombre = nombre
                
                # Descripción y observaciones
                partida.descripcion = request.POST.get('descripcion', '').strip()
                partida.observaciones = request.POST.get('observaciones', '').strip()
                
                # UBICACIÓN ⭐
                bodega_id = request.POST.get('bodega_id')
                if bodega_id:
                    partida.bodega_id = bodega_id
                
                percha = request.POST.get('percha', '').strip()
                if percha:
                    partida.percha = percha
                
                partida.creado_por = request.user
                partida.save()
                
                ubicacion_msg = ""
                if partida.bodega and partida.percha:
                    ubicacion_msg = f" | Ubicación: {partida.bodega.nombre} - {partida.percha}"
                elif partida.bodega:
                    ubicacion_msg = f" | Bodega: {partida.bodega.nombre}"
                
                messages.success(
                    request,
                    f'✅ Partida "{nombre}" creada: {partida.numero_partida}{ubicacion_msg}'
                )
                
                return redirect('detalle_partida', pk=partida.pk)
                
        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    context = {'bodegas': bodegas}  
    return render(request, 'beneficio/partidas/crear.html', context)


# ==========================================
# DETALLE PARTIDA
# ==========================================

@login_required
def detalle_partida(request, pk):
    """Ver detalle completo de una partida"""
    try:
        partida = get_object_or_404(
            Partida.objects.select_related(
                'bodega',
                'creado_por'
            ),
            pk=pk
        )

        # Obtener subpartidas de esta partida
        subpartidas = partida.subpartidas.filter(activo=True).order_by('-fecha_creacion')

        context = {
            'partida': partida,
            'subpartidas': subpartidas,
            'total_subpartidas': subpartidas.count(),
        }

        return render(request, 'beneficio/partidas/detalle_partida.html', context)
    except Exception as e:
        messages.error(request, f'Error al cargar partida: {str(e)}')
        return redirect('lista_partidas')


# ==========================================
# EDITAR PARTIDA
# ==========================================

@login_required
def editar_partida(request, pk):
    partida = get_object_or_404(Partida, pk=pk, activo=True)
    bodegas = Bodega.objects.all()
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Nombre
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError("El nombre es obligatorio")
                partida.nombre = nombre
                
                # Descripción y observaciones
                partida.descripcion = request.POST.get('descripcion', '').strip()
                partida.observaciones = request.POST.get('observaciones', '').strip()
                
                # UBICACIÓN ⭐
                bodega_id = request.POST.get('bodega_id')
                if bodega_id:
                    partida.bodega_id = bodega_id
                else:
                    partida.bodega = None
                
                percha = request.POST.get('percha', '').strip()
                partida.percha = percha if percha else None
                
                partida.save()
                
                messages.success(request, '✅ Partida actualizada')
                return redirect('detalle_partida', pk=partida.pk)
                
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    context = {
        'partida': partida,
        'bodegas': bodegas
    }
    return render(request, 'beneficio/partidas/editar.html', context)



# ==========================================
# ELIMINAR PARTIDA
# ==========================================

@login_required
def eliminar_partida(request, pk):
    """Eliminar una partida (marca como inactiva)"""
    partida = get_object_or_404(Partida, pk=pk)
    lote = partida.lote
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                numero = partida.numero_partida
                peso = partida.peso_neto_kg
                
                # Marcar como inactiva en lugar de eliminar
                partida.activo = False
                partida.save()
                
                # Recalcular peso del lote
                partida.actualizar_peso_lote()
                
                messages.success(
                    request,
                    f'✅ Partida {numero} eliminada exitosamente. '
                    f'Se restaron {peso} kg del lote {lote.codigo}'
                )
                return redirect('detalle_lote', pk=lote.pk)
                
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar partida: {str(e)}')
    
    context = {
        'partida': partida,
    }
    
    return render(request, 'beneficio/partidas/eliminar.html', context)


# ==========================================
# VISTA: PARTIDAS DE UN LOTE ESPECÍFICO
# ==========================================

@login_required
def partidas_de_lote(request, lote_id):
    """
    Muestra todas las partidas de un lote específico
    Vista especializada con estadísticas del lote
    """
    lote = get_object_or_404(Lote, pk=lote_id)
    
    partidas = Partida.objects.filter(
        lote=lote,
        activo=True
    ).select_related('bodega', 'created_by').order_by('-created_at')
    
    # Estadísticas
    total_partidas = partidas.count()
    peso_total_bruto = sum(p.peso_bruto_kg for p in partidas)
    peso_total_tara = sum(p.tara_kg for p in partidas)
    peso_total_neto = sum(p.peso_neto_kg for p in partidas)
    
    context = {
        'lote': lote,
        'partidas': partidas,
        'total_partidas': total_partidas,
        'peso_total_bruto': peso_total_bruto,
        'peso_total_tara': peso_total_tara,
        'peso_total_neto': peso_total_neto,
        'porcentaje_tara_promedio': (peso_total_tara / peso_total_bruto * 100) if peso_total_bruto > 0 else 0,
    }
    
    return render(request, 'beneficio/partidas/partidas_lote.html', context)


@login_required
def editar_partida(request, pk):
    partida = get_object_or_404(Partida, pk=pk, activo=True)
    
    # ⭐ OBTENER BODEGAS
    bodegas = Bodega.objects.all()
    
    if request.method == 'POST':
        print("\n" + "=" * 60)
        print("🔍 DEBUG EDITAR: Formulario recibido")
        print("=" * 60)
        
        # Ver todos los datos recibidos
        print("\nDatos POST recibidos:")
        for key, value in request.POST.items():
            print(f"  {key}: {value}")
        
        try:
            with transaction.atomic():
                # Nombre (obligatorio)
                nombre = request.POST.get('nombre', '').strip()
                print(f"\n✅ Nombre: '{nombre}'")
                
                if not nombre:
                    print("❌ ERROR: Nombre está vacío")
                    raise ValueError("El nombre es obligatorio")
                
                partida.nombre = nombre
                
                # Descripción y observaciones
                descripcion = request.POST.get('descripcion', '').strip()
                observaciones = request.POST.get('observaciones', '').strip()
                
                print(f"✅ Descripción: '{descripcion}'")
                print(f"✅ Observaciones: '{observaciones}'")
                
                partida.descripcion = descripcion
                partida.observaciones = observaciones
                
                # Ubicación
                bodega_id = request.POST.get('bodega_id')
                percha = request.POST.get('percha', '').strip()
                
                print(f"✅ Bodega ID: {bodega_id}")
                print(f"✅ Percha: '{percha}'")
                
                if bodega_id and bodega_id != '':
                    partida.bodega_id = int(bodega_id)
                    print(f"   → Bodega asignada: ID {bodega_id}")
                else:
                    partida.bodega = None
                    print(f"   → Bodega removida")
                
                if percha:
                    partida.percha = percha
                else:
                    partida.percha = None
                
                # Guardar
                print("\n💾 Intentando guardar cambios...")
                partida.save()
                print(f"✅ ¡Partida actualizada exitosamente! ID: {partida.id}")
                
                # Mensaje de éxito
                ubicacion_msg = ""
                if partida.bodega and partida.percha:
                    ubicacion_msg = f" | Ubicación: Bodega #{partida.bodega.id} - {partida.percha}"
                elif partida.bodega:
                    ubicacion_msg = f" | Bodega: Bodega #{partida.bodega.id}"
                
                messages.success(
                    request,
                    f'✅ Partida "{nombre}" actualizada{ubicacion_msg}'
                )
                
                print(f"✅ Redirigiendo a detalle_partida con pk={partida.pk}")
                print("=" * 60 + "\n")
                
                return redirect('detalle_partida', pk=partida.pk)
                
        except ValueError as ve:
            print(f"❌ ValueError: {str(ve)}")
            messages.error(request, f'❌ Error: {str(ve)}')
            print("=" * 60 + "\n")
            
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            print(f"   Tipo: {type(e).__name__}")
            
            import traceback
            print("\n📋 Traceback completo:")
            traceback.print_exc()
            
            messages.error(request, f'❌ Error al actualizar partida: {str(e)}')
            print("=" * 60 + "\n")
    
    # GET request o después de error
    print(f"\n📄 Mostrando formulario de edición para partida {partida.numero_partida}")
    print(f"   Bodegas disponibles: {bodegas.count()}")
    
    context = {
        'partida': partida,
        'bodegas': bodegas,
        'total_bodegas': bodegas.count()
    }
    
    return render(request, 'beneficio/partidas/editar.html', context)


@login_required
def eliminar_partida(request, pk):
    """
    Eliminar (desactivar) partida principal
    """
    partida = get_object_or_404(Partida, pk=pk, activo=True)
    
    if request.method == 'POST':
        try:
            # Soft delete
            partida.activo = False
            partida.save()
            
            # También desactivar todas las sub-partidas
            partida.subpartidas.all().update(activo=False)
            
            messages.success(request, f'✅ Partida "{partida.nombre}" eliminada')
            return redirect('lista_partidas')
            
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar: {str(e)}')
    
    context = {'partida': partida}
    return render(request, 'beneficio/partidas/eliminar.html', context)


# ==========================================
# SUB-PARTIDAS
# ==========================================

@login_required
def agregar_subpartida(request, partida_id):
    """Agregar un Lote de Punto (SubPartida) a una Partida"""
    partida = get_object_or_404(Partida, pk=partida_id, activo=True)

    def safe_decimal(value, default=None):
        """Convertir valor a Decimal de forma segura"""
        if not value or value.strip() == '':
            return default
        try:
            # Reemplazar coma por punto para formato español
            cleaned = value.strip().replace(',', '.')
            return Decimal(cleaned)
        except:
            return default

    if request.method == 'POST':
        try:
            with transaction.atomic():
                subpartida = SubPartida()
                subpartida.partida = partida

                # ID del Lote / Nombre (obligatorio)
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError("El ID del lote es obligatorio")
                subpartida.nombre = nombre

                # Tipo de proceso
                tipo_proceso = request.POST.get('tipo_proceso', 'LAVADO')
                subpartida.tipo_proceso = tipo_proceso

                # Fecha de ingreso
                fecha_ingreso = request.POST.get('fecha_ingreso')
                if fecha_ingreso:
                    subpartida.fecha_ingreso = fecha_ingreso

                # Número de sacos (obligatorio)
                numero_sacos = request.POST.get('numero_sacos', '1')
                subpartida.numero_sacos = int(numero_sacos) if numero_sacos else 1

                # Quintales (obligatorio)
                quintales_val = safe_decimal(request.POST.get('quintales', '0'), Decimal('0'))
                if quintales_val <= 0:
                    raise ValueError("Los quintales son obligatorios y deben ser mayores a 0")
                subpartida.quintales = quintales_val

                # Calcular peso en kg desde quintales (1 qq = 46 kg)
                peso_bruto_val = safe_decimal(request.POST.get('peso_bruto', '0'), Decimal('0'))
                if peso_bruto_val > 0:
                    subpartida.peso_bruto_kg = peso_bruto_val
                else:
                    subpartida.peso_bruto_kg = quintales_val * 46

                subpartida.tara_kg = safe_decimal(request.POST.get('tara', '0'), Decimal('0'))
                subpartida.unidad_medida = 'qq'

                # Humedad
                subpartida.humedad = safe_decimal(request.POST.get('humedad', ''))

                # UBICACIÓN (Fila)
                fila = request.POST.get('fila', '').strip()
                if fila:
                    subpartida.fila = fila

                # Etiqueta
                etiqueta = request.POST.get('etiqueta', '').strip()
                if etiqueta:
                    subpartida.etiqueta = etiqueta
                    # Crear la etiqueta en el catálogo si no existe
                    EtiquetaLote.objects.get_or_create(nombre=etiqueta)

                # === Campos de Análisis de Calidad ===
                subpartida.rendimiento_b15 = safe_decimal(request.POST.get('rendimiento_b15', ''))
                subpartida.defectos = safe_decimal(request.POST.get('defectos', ''))
                subpartida.rb = safe_decimal(request.POST.get('rb', ''))
                subpartida.rn = safe_decimal(request.POST.get('rn', ''))
                subpartida.score = safe_decimal(request.POST.get('score', ''))

                # === Campos adicionales de catación ===
                subpartida.peso_cp = safe_decimal(request.POST.get('peso_cp', ''))
                subpartida.oro_sucio = safe_decimal(request.POST.get('oro_sucio', ''))
                subpartida.oro_limpio = safe_decimal(request.POST.get('oro_limpio', ''))

                granulometria = request.POST.get('granulometria', '').strip()
                if granulometria:
                    subpartida.granulometria = granulometria

                subpartida.bz_gramos = safe_decimal(request.POST.get('bz_gramos', ''))
                subpartida.bz_porcentaje = safe_decimal(request.POST.get('bz_porcentaje', ''))
                subpartida.defectos_fisicos = safe_decimal(request.POST.get('defectos_fisicos', ''))
                subpartida.defectos_verdes = safe_decimal(request.POST.get('defectos_verdes', ''))

                # === Calidad de Taza ===
                taza = request.POST.get('taza', '').strip()
                if taza:
                    subpartida.taza = taza

                cualidades = request.POST.get('cualidades', '').strip()
                if cualidades:
                    subpartida.cualidades = cualidades

                perfil_sensorial = request.POST.get('perfil_sensorial', '').strip()
                if perfil_sensorial:
                    subpartida.perfil_sensorial = perfil_sensorial

                # Otros campos
                proveedor = request.POST.get('proveedor', '').strip()
                if proveedor:
                    subpartida.proveedor = proveedor

                subpartida.observaciones = request.POST.get('observaciones', '').strip()
                subpartida.creado_por = request.user

                subpartida.save()

                ubicacion_msg = f" | Fila: {fila}" if fila else ""

                messages.success(
                    request,
                    f'✅ Lote agregado: {subpartida.numero_subpartida} - {nombre}{ubicacion_msg}'
                )

                return redirect('detalle_partida', pk=partida.pk)

        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    etiquetas = EtiquetaLote.objects.all()
    context = {'partida': partida, 'etiquetas': etiquetas}
    return render(request, 'beneficio/partidas/agregar_subpartida.html', context)


@login_required
def control_etiquetas(request):
    """Vista para Control de Partidas - Dashboard con gráficas y estadísticas"""
    from django.db.models import Count, Sum, Avg
    from django.core.serializers.json import DjangoJSONEncoder
    import json

    etiqueta_seleccionada = request.GET.get('etiqueta', '')

    # Obtener TODAS las subpartidas activas para estadísticas generales
    todas_subpartidas = SubPartida.objects.filter(activo=True)

    # Obtener etiquetas únicas que están en uso en las subpartidas
    etiquetas = todas_subpartidas.filter(
        etiqueta__isnull=False
    ).exclude(etiqueta='').values_list('etiqueta', flat=True).distinct().order_by('etiqueta')

    # Subpartidas filtradas por etiqueta si se seleccionó una
    if etiqueta_seleccionada:
        subpartidas = todas_subpartidas.filter(
            etiqueta__iexact=etiqueta_seleccionada
        ).select_related('partida', 'partida__bodega').order_by('-fecha_creacion')
    else:
        subpartidas = todas_subpartidas.select_related('partida', 'partida__bodega').order_by('-fecha_creacion')

    # === ESTADÍSTICAS GENERALES ===
    totales_generales = todas_subpartidas.aggregate(
        total_lotes=Count('id'),
        total_quintales=Sum('quintales'),
        total_sacos=Sum('numero_sacos'),
        promedio_quintales=Avg('quintales')
    )

    # Total de partidas activas
    total_partidas = Partida.objects.filter(activo=True).count()

    # Calcular totales de las subpartidas filtradas
    totales_filtrados = subpartidas.aggregate(
        total_quintales=Sum('quintales'),
        total_sacos=Sum('numero_sacos')
    )

    # === DATOS PARA GRÁFICAS ===

    # 1. Distribución por Tipo de Proceso
    stats_proceso = list(todas_subpartidas.values('tipo_proceso').annotate(
        total_lotes=Count('id'),
        total_quintales=Sum('quintales')
    ).order_by('-total_quintales'))

    # 2. Distribución por Etiqueta (top 10)
    stats_etiquetas = list(todas_subpartidas.filter(
        etiqueta__isnull=False
    ).exclude(etiqueta='').values('etiqueta').annotate(
        total_lotes=Count('id'),
        total_quintales=Sum('quintales'),
        total_sacos=Sum('numero_sacos')
    ).order_by('-total_quintales')[:10])

    # 3. Distribución por Bodega
    stats_bodega = list(todas_subpartidas.filter(
        partida__bodega__isnull=False
    ).values('partida__bodega__nombre').annotate(
        total_lotes=Count('id'),
        total_quintales=Sum('quintales')
    ).order_by('-total_quintales'))

    # 4. Distribución por Calidad de Taza
    stats_taza = list(todas_subpartidas.filter(
        taza__isnull=False
    ).exclude(taza='').values('taza').annotate(
        total_lotes=Count('id'),
        total_quintales=Sum('quintales')
    ).order_by('-total_quintales'))

    # 5. Top 5 Partidas con más quintales
    top_partidas = list(Partida.objects.filter(activo=True).annotate(
        total_qq=Sum('subpartidas__quintales')
    ).filter(total_qq__gt=0).order_by('-total_qq')[:5].values('numero_partida', 'nombre', 'total_qq'))

    # Convertir a JSON para las gráficas
    context = {
        'etiquetas': etiquetas,
        'etiqueta_seleccionada': etiqueta_seleccionada,
        'subpartidas': subpartidas[:50],  # Limitar a 50 para rendimiento
        'total_subpartidas': subpartidas.count(),
        'stats_etiquetas': stats_etiquetas,
        'total_quintales': totales_filtrados['total_quintales'] or 0,
        'total_sacos': totales_filtrados['total_sacos'] or 0,
        # Estadísticas generales
        'totales_generales': totales_generales,
        'total_partidas': total_partidas,
        # Datos JSON para gráficas (usar DjangoJSONEncoder para manejar Decimal)
        'stats_proceso_json': json.dumps(stats_proceso, cls=DjangoJSONEncoder),
        'stats_etiquetas_json': json.dumps(stats_etiquetas, cls=DjangoJSONEncoder),
        'stats_bodega_json': json.dumps(stats_bodega, cls=DjangoJSONEncoder),
        'stats_taza_json': json.dumps(stats_taza, cls=DjangoJSONEncoder),
        'top_partidas_json': json.dumps(top_partidas, cls=DjangoJSONEncoder),
    }
    return render(request, 'beneficio/partidas/control_etiquetas.html', context)


@login_required
def editar_subpartida(request, pk):
    """Editar un Lote de Punto (SubPartida)"""
    subpartida = get_object_or_404(SubPartida, pk=pk, activo=True)

    def safe_decimal(value, default=None):
        """Convertir valor a Decimal de forma segura"""
        if not value or value.strip() == '':
            return default
        try:
            # Reemplazar coma por punto para formato español
            cleaned = value.strip().replace(',', '.')
            return Decimal(cleaned)
        except:
            return default

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ID del Lote / Nombre (obligatorio)
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError("El ID del lote es obligatorio")
                subpartida.nombre = nombre

                # Tipo de proceso
                tipo_proceso = request.POST.get('tipo_proceso', 'LAVADO')
                subpartida.tipo_proceso = tipo_proceso

                # Fecha de ingreso
                fecha_ingreso = request.POST.get('fecha_ingreso')
                subpartida.fecha_ingreso = fecha_ingreso if fecha_ingreso else None

                # Número de sacos
                numero_sacos = request.POST.get('numero_sacos', '1')
                subpartida.numero_sacos = int(numero_sacos) if numero_sacos else 1

                # Quintales (obligatorio)
                quintales_val = safe_decimal(request.POST.get('quintales', '0'), Decimal('0'))
                if quintales_val <= 0:
                    raise ValueError("Los quintales son obligatorios y deben ser mayores a 0")
                subpartida.quintales = quintales_val

                # Calcular peso en kg desde quintales (1 qq = 46 kg)
                peso_bruto_val = safe_decimal(request.POST.get('peso_bruto', '0'), Decimal('0'))
                if peso_bruto_val > 0:
                    subpartida.peso_bruto_kg = peso_bruto_val
                else:
                    subpartida.peso_bruto_kg = quintales_val * 46

                subpartida.tara_kg = safe_decimal(request.POST.get('tara', '0'), Decimal('0'))
                subpartida.unidad_medida = 'qq'

                # Humedad
                subpartida.humedad = safe_decimal(request.POST.get('humedad', ''))

                # UBICACIÓN (Fila)
                fila = request.POST.get('fila', '').strip()
                subpartida.fila = fila if fila else None

                # === Campos de Análisis de Calidad ===
                subpartida.rendimiento_b15 = safe_decimal(request.POST.get('rendimiento_b15', ''))
                subpartida.defectos = safe_decimal(request.POST.get('defectos', ''))
                subpartida.rb = safe_decimal(request.POST.get('rb', ''))
                subpartida.rn = safe_decimal(request.POST.get('rn', ''))
                subpartida.score = safe_decimal(request.POST.get('score', ''))

                # === Calidad de Taza ===
                taza = request.POST.get('taza', '').strip()
                subpartida.taza = taza if taza else None

                cualidades = request.POST.get('cualidades', '').strip()
                subpartida.cualidades = cualidades if cualidades else None

                # === Datos de Catación ===
                subpartida.peso_cp = safe_decimal(request.POST.get('peso_cp', ''))
                subpartida.oro_sucio = safe_decimal(request.POST.get('oro_sucio', ''))
                subpartida.oro_limpio = safe_decimal(request.POST.get('oro_limpio', ''))

                granulometria = request.POST.get('granulometria', '').strip()
                subpartida.granulometria = granulometria if granulometria else None

                subpartida.bz_gramos = safe_decimal(request.POST.get('bz_gramos', ''))
                subpartida.bz_porcentaje = safe_decimal(request.POST.get('bz_porcentaje', ''))
                subpartida.defectos_fisicos = safe_decimal(request.POST.get('defectos_fisicos', ''))
                subpartida.defectos_verdes = safe_decimal(request.POST.get('defectos_verdes', ''))

                perfil_sensorial = request.POST.get('perfil_sensorial', '').strip()
                subpartida.perfil_sensorial = perfil_sensorial if perfil_sensorial else None

                # Otros campos
                proveedor = request.POST.get('proveedor', '').strip()
                subpartida.proveedor = proveedor if proveedor else None

                subpartida.observaciones = request.POST.get('observaciones', '').strip()

                subpartida.save()

                messages.success(request, f'✅ Lote "{nombre}" actualizado correctamente')
                return redirect('detalle_partida', pk=subpartida.partida.pk)

        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {'subpartida': subpartida}
    return render(request, 'beneficio/partidas/editar_subpartida.html', context)


@login_required
def eliminar_subpartida(request, pk):
    """
    Eliminar sub-partida
    """
    subpartida = get_object_or_404(SubPartida, pk=pk, activo=True)
    partida_id = subpartida.partida.pk
    
    if request.method == 'POST':
        try:
            # Soft delete
            subpartida.activo = False
            subpartida.save()
            
            messages.success(request, '✅ Sub-partida eliminada')
            return redirect('detalle_partida', pk=partida_id)
            
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar: {str(e)}')
    
    context = {'subpartida': subpartida}
    return render(request, 'beneficio/partidas/eliminar_subpartida.html', context)


# ==========================================
# VISTA DE DETALLE DE SUB-PARTIDA
# ==========================================

@login_required
def detalle_subpartida(request, pk):
    """
    Ver detalle completo de una sub-partida
    """
    subpartida = get_object_or_404(SubPartida, pk=pk, activo=True)
    movimientos = subpartida.movimientos.all().order_by('-fecha')

    context = {
        'subpartida': subpartida,
        'movimientos': movimientos,
    }
    return render(request, 'beneficio/partidas/detalle_subpartida.html', context)


# ==========================================
# MOVIMIENTOS DE SUBPARTIDA (Trazabilidad)
# ==========================================

@login_required
def procesar_subpartida(request, pk):
    """
    Crear un movimiento de salida desde una SubPartida hacia un proceso
    """
    subpartida = get_object_or_404(SubPartida, pk=pk, activo=True)

    # Verificar que hay quintales disponibles
    if subpartida.quintales_disponibles <= 0:
        messages.error(request, '❌ Esta subpartida no tiene quintales disponibles para procesar')
        return redirect('detalle_subpartida', pk=pk)

    # Obtener procesados, reprocesos y mezclas disponibles para seleccionar
    procesados = Procesado.objects.filter(finalizado=False).order_by('-fecha')
    reprocesos = Reproceso.objects.all().order_by('-fecha')[:50]
    mezclas = Mezcla.objects.all().order_by('-fecha')[:50]

    if request.method == 'POST':
        try:
            tipo_destino = request.POST.get('tipo_destino')
            quintales_str = request.POST.get('quintales_movidos', '0')
            observaciones = request.POST.get('observaciones', '')

            # Validar quintales
            try:
                quintales_movidos = Decimal(quintales_str)
            except:
                messages.error(request, '❌ Cantidad de quintales inválida')
                return redirect('procesar_subpartida', pk=pk)

            if quintales_movidos <= 0:
                messages.error(request, '❌ La cantidad debe ser mayor a 0')
                return redirect('procesar_subpartida', pk=pk)

            if quintales_movidos > subpartida.quintales_disponibles:
                messages.error(
                    request,
                    f'❌ Solo hay {subpartida.quintales_disponibles:.2f} qq disponibles'
                )
                return redirect('procesar_subpartida', pk=pk)

            # Crear el movimiento
            movimiento = MovimientoSubPartida(
                subpartida=subpartida,
                tipo_destino=tipo_destino,
                quintales_movidos=quintales_movidos,
                observaciones=observaciones,
                creado_por=request.user
            )

            # Asignar referencia según tipo de destino
            if tipo_destino == 'PROCESADO':
                procesado_id = request.POST.get('procesado_id')
                if procesado_id:
                    movimiento.procesado_id = procesado_id
            elif tipo_destino == 'REPROCESO':
                reproceso_id = request.POST.get('reproceso_id')
                if reproceso_id:
                    movimiento.reproceso_id = reproceso_id
            elif tipo_destino == 'MEZCLA':
                mezcla_id = request.POST.get('mezcla_id')
                if mezcla_id:
                    movimiento.mezcla_id = mezcla_id

            movimiento.save()

            messages.success(
                request,
                f'✅ Movimiento registrado: {quintales_movidos:.2f} qq hacia {movimiento.get_tipo_destino_display()}'
            )
            return redirect('detalle_subpartida', pk=pk)

        except Exception as e:
            messages.error(request, f'❌ Error al registrar movimiento: {str(e)}')

    context = {
        'subpartida': subpartida,
        'procesados': procesados,
        'reprocesos': reprocesos,
        'mezclas': mezclas,
        'tipos_destino': MovimientoSubPartida.TIPO_DESTINO_CHOICES,
    }
    return render(request, 'beneficio/partidas/procesar_subpartida.html', context)


@login_required
def eliminar_movimiento(request, pk):
    """
    Eliminar un movimiento de SubPartida
    """
    movimiento = get_object_or_404(MovimientoSubPartida, pk=pk)
    subpartida_pk = movimiento.subpartida.pk

    if request.method == 'POST':
        try:
            movimiento.delete()
            messages.success(request, '✅ Movimiento eliminado correctamente')
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar: {str(e)}')

    return redirect('detalle_subpartida', pk=subpartida_pk)


# ==========================================
# BENEFICIADO FINCA - TRABAJADORES
# ==========================================

@login_required
@user_passes_test(lambda u: u.is_staff)
def lista_trabajadores_view(request):
    """Lista de trabajadores de la finca - Solo administradores"""
    trabajadores = Trabajador.objects.all().order_by('nombre_completo')

    # Filtro por estado (activo/inactivo)
    estado = request.GET.get('estado')
    if estado == 'activos':
        trabajadores = trabajadores.filter(activo=True)
    elif estado == 'inactivos':
        trabajadores = trabajadores.filter(activo=False)

    # Búsqueda por nombre o cédula
    busqueda = request.GET.get('busqueda', '').strip()
    if busqueda:
        trabajadores = trabajadores.filter(
            Q(nombre_completo__icontains=busqueda) |
            Q(cedula__icontains=busqueda)
        )

    context = {
        'trabajadores': trabajadores,
        'estado': estado,
        'busqueda': busqueda,
    }
    return render(request, 'beneficio/beneficiado_finca/lista_trabajadores.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def crear_trabajador_view(request):
    """Crear nuevo trabajador - Solo administradores"""
    if request.method == 'POST':
        try:
            trabajador = Trabajador()

            # Nombre completo (obligatorio)
            nombre = request.POST.get('nombre_completo', '').strip()
            if not nombre:
                raise ValueError("El nombre completo es obligatorio")
            trabajador.nombre_completo = nombre

            # Campos opcionales
            trabajador.cedula = request.POST.get('cedula', '').strip() or None
            trabajador.telefono = request.POST.get('telefono', '').strip() or None
            trabajador.activo = request.POST.get('activo') == 'on'

            trabajador.save()

            messages.success(request, f'✅ Trabajador "{trabajador.nombre_completo}" creado correctamente')
            return redirect('lista_trabajadores')

        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error al crear trabajador: {str(e)}')

    return render(request, 'beneficio/beneficiado_finca/form_trabajador.html', {'editar': False})


@login_required
@user_passes_test(lambda u: u.is_staff)
def editar_trabajador_view(request, pk):
    """Editar trabajador existente - Solo administradores"""
    trabajador = get_object_or_404(Trabajador, pk=pk)

    if request.method == 'POST':
        try:
            # Nombre completo (obligatorio)
            nombre = request.POST.get('nombre_completo', '').strip()
            if not nombre:
                raise ValueError("El nombre completo es obligatorio")
            trabajador.nombre_completo = nombre

            # Campos opcionales
            trabajador.cedula = request.POST.get('cedula', '').strip() or None
            trabajador.telefono = request.POST.get('telefono', '').strip() or None
            trabajador.activo = request.POST.get('activo') == 'on'

            trabajador.save()

            messages.success(request, f'✅ Trabajador "{trabajador.nombre_completo}" actualizado')
            return redirect('lista_trabajadores')

        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar: {str(e)}')

    context = {
        'trabajador': trabajador,
        'editar': True,
    }
    return render(request, 'beneficio/beneficiado_finca/form_trabajador.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def eliminar_trabajador_view(request, pk):
    """Eliminar trabajador (soft delete) - Solo administradores"""
    trabajador = get_object_or_404(Trabajador, pk=pk)

    if request.method == 'POST':
        try:
            trabajador.activo = False
            trabajador.save()
            messages.success(request, f'✅ Trabajador "{trabajador.nombre_completo}" desactivado')
            return redirect('lista_trabajadores')
        except Exception as e:
            messages.error(request, f'❌ Error al desactivar: {str(e)}')

    context = {'trabajador': trabajador}
    return render(request, 'beneficio/beneficiado_finca/eliminar_trabajador.html', context)


# ==========================================
# BENEFICIADO FINCA - PLANILLAS SEMANALES
# ==========================================

@login_required
@user_passes_test(lambda u: u.is_staff)
def lista_planillas_view(request):
    """Lista de planillas semanales - Solo administradores"""
    planillas = PlanillaSemanal.objects.all().order_by('-fecha_inicio')

    # Filtro por año
    anio = request.GET.get('anio')
    if anio:
        planillas = planillas.filter(fecha_inicio__year=anio)

    # Filtro por mes
    mes = request.GET.get('mes')
    if mes:
        planillas = planillas.filter(fecha_inicio__month=mes)

    context = {
        'planillas': planillas,
        'anio': anio,
        'mes': mes,
    }
    return render(request, 'beneficio/beneficiado_finca/lista_planillas.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def crear_planilla_view(request):
    """Crear nueva planilla semanal - Solo administradores"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                planilla = PlanillaSemanal()

                # Fechas (obligatorias)
                fecha_inicio = request.POST.get('fecha_inicio')
                fecha_fin = request.POST.get('fecha_fin')

                if not fecha_inicio or not fecha_fin:
                    raise ValueError("Las fechas de inicio y fin son obligatorias")

                planilla.fecha_inicio = fecha_inicio
                planilla.fecha_fin = fecha_fin
                planilla.observaciones = request.POST.get('observaciones', '').strip()
                planilla.created_by = request.user

                planilla.save()

                messages.success(request, f'✅ Planilla semanal creada: {planilla.fecha_inicio} - {planilla.fecha_fin}')
                return redirect('detalle_planilla', pk=planilla.pk)

        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error al crear planilla: {str(e)}')

    return render(request, 'beneficio/beneficiado_finca/crear_planilla.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
def detalle_planilla_view(request, pk):
    """Vista detallada de planilla semanal con tabla de trabajadores × días - Solo administradores"""
    planilla = get_object_or_404(PlanillaSemanal, pk=pk)

    # Obtener todos los trabajadores activos
    trabajadores = Trabajador.objects.filter(activo=True).order_by('nombre_completo')

    # Obtener todos los registros de esta planilla
    registros = planilla.registros_diarios.select_related('trabajador', 'tipo_cafe').all()

    # Crear diccionario de registros: {trabajador_id: {dia: registro}}
    registros_dict = {}
    for registro in registros:
        if registro.trabajador_id not in registros_dict:
            registros_dict[registro.trabajador_id] = {}
        registros_dict[registro.trabajador_id][registro.dia_semana] = registro

    # Días de la semana
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']

    # Preparar datos para la tabla
    tabla_datos = []
    for trabajador in trabajadores:
        fila = {
            'trabajador': trabajador,
            'registros_dias': {},
            'total_libras': Decimal('0.00'),
        }

        for dia in dias:
            if trabajador.id in registros_dict and dia in registros_dict[trabajador.id]:
                registro = registros_dict[trabajador.id][dia]
                fila['registros_dias'][dia] = registro
                fila['total_libras'] += registro.libras_cortadas
            else:
                fila['registros_dias'][dia] = None

        # Calcular quintales
        fila['total_qq'] = fila['total_libras'] / Decimal('100.00')
        tabla_datos.append(fila)

    # Totales por día
    totales_dias = {}
    for dia in dias:
        total = registros.filter(dia_semana=dia).aggregate(
            total=Sum('libras_cortadas')
        )['total'] or Decimal('0.00')
        totales_dias[dia] = total

    # Totales por tipo de café
    totales_cafe = {}
    for registro in registros:
        tipo = registro.get_tipo_cafe_display_full()
        if tipo not in totales_cafe:
            totales_cafe[tipo] = Decimal('0.00')
        totales_cafe[tipo] += registro.libras_cortadas

    context = {
        'planilla': planilla,
        'tabla_datos': tabla_datos,
        'dias': dias,
        'totales_dias': totales_dias,
        'totales_cafe': totales_cafe,
    }
    return render(request, 'beneficio/beneficiado_finca/detalle_planilla.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def editar_planilla_view(request, pk):
    """Editar planilla semanal - Solo administradores"""
    planilla = get_object_or_404(PlanillaSemanal, pk=pk)

    if request.method == 'POST':
        try:
            # Fechas (obligatorias)
            fecha_inicio = request.POST.get('fecha_inicio')
            fecha_fin = request.POST.get('fecha_fin')

            if not fecha_inicio or not fecha_fin:
                raise ValueError("Las fechas de inicio y fin son obligatorias")

            planilla.fecha_inicio = fecha_inicio
            planilla.fecha_fin = fecha_fin
            planilla.observaciones = request.POST.get('observaciones', '').strip()

            planilla.save()

            messages.success(request, '✅ Planilla actualizada correctamente')
            return redirect('detalle_planilla', pk=planilla.pk)

        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar: {str(e)}')

    context = {'planilla': planilla}
    return render(request, 'beneficio/beneficiado_finca/editar_planilla.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def eliminar_planilla_view(request, pk):
    """Eliminar planilla semanal y todos sus registros - Solo administradores"""
    planilla = get_object_or_404(PlanillaSemanal, pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Eliminar todos los registros asociados
                planilla.registros_diarios.all().delete()
                # Eliminar la planilla
                planilla.delete()

                messages.success(request, '✅ Planilla eliminada correctamente')
                return redirect('lista_planillas')

        except Exception as e:
            messages.error(request, f'❌ Error al eliminar: {str(e)}')

    context = {'planilla': planilla}
    return render(request, 'beneficio/beneficiado_finca/eliminar_planilla.html', context)


# ==========================================
# BENEFICIADO FINCA - REGISTROS DIARIOS
# ==========================================

@login_required
@user_passes_test(lambda u: u.is_staff)
def agregar_registro_view(request, planilla_id):
    """Agregar o editar registro diario - Solo administradores"""
    planilla = get_object_or_404(PlanillaSemanal, pk=planilla_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener parámetros
                trabajador_id = request.POST.get('trabajador_id')
                dia_semana = request.POST.get('dia_semana')
                fecha = request.POST.get('fecha')

                if not trabajador_id or not dia_semana or not fecha:
                    raise ValueError("Trabajador, día y fecha son obligatorios")

                trabajador = get_object_or_404(Trabajador, pk=trabajador_id)

                # Buscar registro existente o crear nuevo
                registro, created = RegistroDiario.objects.get_or_create(
                    planilla=planilla,
                    trabajador=trabajador,
                    dia_semana=dia_semana,
                    fecha=fecha,
                    defaults={
                        'libras_cortadas': Decimal('0.00')
                    }
                )

                # Actualizar campos
                libras = request.POST.get('libras_cortadas', '0').strip()
                registro.libras_cortadas = Decimal(libras) if libras else Decimal('0.00')

                # Tipo de café - dual selection
                tipo_cafe_id = request.POST.get('tipo_cafe')
                tipo_cafe_manual = request.POST.get('tipo_cafe_manual', '').strip()

                if tipo_cafe_id:
                    registro.tipo_cafe_id = tipo_cafe_id
                    registro.tipo_cafe_manual = None
                elif tipo_cafe_manual:
                    registro.tipo_cafe = None
                    registro.tipo_cafe_manual = tipo_cafe_manual
                else:
                    registro.tipo_cafe = None
                    registro.tipo_cafe_manual = None

                registro.observaciones = request.POST.get('observaciones', '').strip()

                registro.save()

                action_text = "agregado" if created else "actualizado"
                messages.success(request, f'✅ Registro {action_text} correctamente')
                return redirect('detalle_planilla', pk=planilla.pk)

        except ValueError as ve:
            messages.error(request, f'❌ Error: {str(ve)}')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    # GET request - mostrar formulario
    trabajadores = Trabajador.objects.filter(activo=True).order_by('nombre_completo')
    tipos_cafe = TipoCafe.objects.all().order_by('nombre')

    # Obtener registro si existe (para edición)
    registro = None
    trabajador_id = request.GET.get('trabajador_id')
    dia_semana = request.GET.get('dia_semana')

    if trabajador_id and dia_semana:
        try:
            registro = RegistroDiario.objects.get(
                planilla=planilla,
                trabajador_id=trabajador_id,
                dia_semana=dia_semana
            )
        except RegistroDiario.DoesNotExist:
            pass

    context = {
        'planilla': planilla,
        'trabajadores': trabajadores,
        'tipos_cafe': tipos_cafe,
        'registro': registro,
        'dias_choices': RegistroDiario.DIAS_SEMANA,
    }
    return render(request, 'beneficio/beneficiado_finca/agregar_registro.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def eliminar_registro_view(request, pk):
    """Eliminar registro diario - Solo administradores"""
    registro = get_object_or_404(RegistroDiario, pk=pk)
    planilla_id = registro.planilla.pk

    if request.method == 'POST':
        try:
            registro.delete()
            messages.success(request, '✅ Registro eliminado correctamente')
            return redirect('detalle_planilla', pk=planilla_id)
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar: {str(e)}')

    context = {'registro': registro}
    return render(request, 'beneficio/beneficiado_finca/eliminar_registro.html', context)
















