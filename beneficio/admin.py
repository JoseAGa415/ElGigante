from django.contrib import admin
from beneficio.models import (
    TipoCafe, Bodega, Lote, Procesado,
    Reproceso, Mezcla, DetalleMezcla,
    Catacion, DefectoCatacion, Compra, Comprador,
    MantenimientoPlanta, HistorialMantenimiento,
    ReciboCafe, Trabajador, PlanillaSemanal, RegistroDiario
)

@admin.register(TipoCafe)
class TipoCafeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'created_at']
    search_fields = ['nombre']

#@admin.register(Bodega)
#class BodegaAdmin(admin.ModelAdmin):
#    list_display = ['nombre', 'capacidad_kg', 'ubicacion', 'activo', 'responsable']
#    list_filter = ['codigo']

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'tipo_cafe', 'bodega', 'peso_kg', 'proveedor', 'fecha_ingreso', 'activo']
    list_filter = ['bodega', 'tipo_cafe', 'activo', 'fecha_ingreso']
    search_fields = ['codigo', 'proveedor']
    date_hierarchy = 'fecha_ingreso'

@admin.register(Procesado)
class ProcesadoAdmin(admin.ModelAdmin):
    list_display = ['numero_trilla', 'lote', 'fecha', 'peso_inicial_kg', 'peso_final_kg']
    list_filter = ['fecha']
    search_fields = ['lote__codigo']
    date_hierarchy = 'fecha'

@admin.register(Reproceso)
class ReprocesoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'procesado', 'fecha', 'peso_inicial_kg', 'peso_final_kg']
    list_filter = ['fecha']
    date_hierarchy = 'fecha'

@admin.register(Mezcla)
class MezclaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fecha', 'peso_total_kg', 'destino', 'responsable']
    list_filter = ['fecha', 'destino']
    search_fields = ['destino']
    date_hierarchy = 'fecha'

@admin.register(DetalleMezcla)
class DetalleMezclaAdmin(admin.ModelAdmin):
    list_display = ['mezcla', 'lote', 'peso_kg', 'porcentaje']
    list_filter = ['mezcla']

@admin.register(Catacion)
class CatacionAdmin(admin.ModelAdmin):
    list_display = ['codigo_muestra', 'fecha_catacion', 'tipo_muestra', 'puntaje_total', 'clasificacion', 'catador']
    list_filter = ['tipo_muestra', 'clasificacion', 'fecha_catacion']
    search_fields = ['codigo_muestra']
    date_hierarchy = 'fecha_catacion'
    readonly_fields = ['puntaje_total', 'clasificacion']

@admin.register(DefectoCatacion)
class DefectoCatacionAdmin(admin.ModelAdmin):
    list_display = ['catacion', 'categoria', 'tipo_defecto', 'cantidad', 'equivalente_defectos']
    list_filter = ['categoria']

@admin.register(Comprador)
class CompradorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'empresa', 'telefono', 'total_compras', 'monto_total_comprado', 'activo']
    list_filter = ['activo', 'created_at']
    search_fields = ['nombre', 'empresa', 'email']
    date_hierarchy = 'created_at'

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ['comprador', 'fecha_compra', 'cantidad', 'unidad', 'precio_unitario', 'monto_total', 'estado_pago']
    list_filter = ['estado_pago', 'unidad', 'fecha_compra']
    search_fields = ['comprador__nombre', 'numero_factura', 'descripcion']
    date_hierarchy = 'fecha_compra'
    readonly_fields = ['monto_total']

@admin.register(MantenimientoPlanta)
class MantenimientoPlantaAdmin(admin.ModelAdmin):
    list_display = ['horas_acumuladas', 'limite_horas', 'porcentaje_uso', 'estado', 'horas_restantes']
    readonly_fields = ['horas_acumuladas', 'porcentaje_uso', 'horas_restantes']

@admin.register(HistorialMantenimiento)
class HistorialMantenimientoAdmin(admin.ModelAdmin):
    list_display = ['fecha_mantenimiento', 'tipo_mantenimiento', 'horas_acumuladas', 'realizado_por', 'costo']
    list_filter = ['tipo_mantenimiento', 'fecha_mantenimiento']
    date_hierarchy = 'fecha_mantenimiento'

@admin.register(ReciboCafe)
class ReciboCafeAdmin(admin.ModelAdmin):
    list_display = ['numero_recibo', 'lote', 'fecha_recibo', 'peso', 'unidad', 'proveedor', 'monto_total']
    list_filter = ['fecha_recibo', 'unidad']
    search_fields = ['numero_recibo', 'lote__codigo', 'proveedor']
    date_hierarchy = 'fecha_recibo'
    readonly_fields = ['numero_recibo', 'monto_total']

# ========== BENEFICIADO FINCA ==========

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'cedula', 'telefono', 'activo', 'created_at']
    list_filter = ['activo', 'created_at']
    search_fields = ['nombre_completo', 'cedula', 'telefono']
    date_hierarchy = 'created_at'

@admin.register(PlanillaSemanal)
class PlanillaSemanalAdmin(admin.ModelAdmin):
    list_display = ['fecha_inicio', 'fecha_fin', 'created_by', 'created_at']
    list_filter = ['fecha_inicio', 'created_at']
    search_fields = ['observaciones', 'created_by__username']
    date_hierarchy = 'fecha_inicio'
    readonly_fields = ['created_at', 'updated_at']

@admin.register(RegistroDiario)
class RegistroDiarioAdmin(admin.ModelAdmin):
    list_display = ['planilla', 'trabajador', 'dia_semana', 'fecha', 'libras_cortadas', 'get_tipo_cafe_display_full']
    list_filter = ['dia_semana', 'fecha', 'planilla']
    search_fields = ['trabajador__nombre_completo', 'tipo_cafe_manual']
    date_hierarchy = 'fecha'
    raw_id_fields = ['planilla', 'trabajador', 'tipo_cafe']