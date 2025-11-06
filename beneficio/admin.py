from django.contrib import admin
from beneficio.models import (
    TipoCafe, Bodega, Lote, Procesado, 
    Reproceso, Mezcla, DetalleMezcla,
    Catacion, DefectoCatacion
)

@admin.register(TipoCafe)
class TipoCafeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'created_at']
    search_fields = ['nombre']

@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'capacidad_kg', 'ubicacion', 'responsable', 'espacio_disponible']
    list_filter = ['codigo']

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