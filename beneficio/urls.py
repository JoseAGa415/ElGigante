from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Historial
    path('historial/', views.historial, name='historial'),
    
    # Lotes
    path('lotes/', views.lista_lotes, name='lista_lotes'),
    path('lotes/crear/', views.crear_lote, name='crear_lote'),
    path('lotes/<int:pk>/', views.detalle_lote, name='detalle_lote'),
    path('lotes/<int:pk>/editar/', views.editar_lote, name='editar_lote'),
    path('lotes/<int:pk>/eliminar/', views.eliminar_lote, name='eliminar_lote'),
    
    # Procesados
    path('procesados/', views.lista_procesados, name='lista_procesados'),
    path('procesados/seleccionar-lote/', views.seleccionar_lote_procesar, name='seleccionar_lote_procesar'),
    path('lotes/<int:lote_id>/procesar/', views.crear_procesado, name='crear_procesado'),
    path('procesados/<int:pk>/', views.detalle_procesado, name='detalle_procesado'),
    path('procesados/<int:pk>/editar/', views.editar_procesado, name='editar_procesado'),
    path('procesados/<int:pk>/eliminar/', views.eliminar_procesado, name='eliminar_procesado'),
    path('procesados/<int:procesado_id>/continuar/', views.continuar_procesado, name='continuar_procesado'),
    path('recibos/<int:recibo_id>/procesar/', views.crear_procesado_desde_recibo, name='procesar_desde_recibo'),
    
    # Reprocesos
    path('reprocesos/', views.lista_reprocesos, name='lista_reprocesos'),
    path('reprocesos/<int:pk>/', views.detalle_reproceso, name='detalle_reproceso'),
    path('reprocesos/<int:pk>/editar/', views.editar_reproceso, name='editar_reproceso'),
    path('reprocesos/<int:pk>/reprocesar/', views.reprocesar_reproceso, name='reprocesar_reproceso'),
    path('procesados/<int:procesado_id>/reprocesar/', views.crear_reproceso, name='crear_reproceso'),
    
    # --- ¡ESTA LÍNEA FALTABA! ---
    path('reprocesos/<int:pk>/eliminar/', views.eliminar_reproceso, name='eliminar_reproceso'),
    
    # Mezclas
    path('mezclas/', views.lista_mezclas, name='lista_mezclas'),
    path('mezclas/crear/', views.crear_mezcla, name='crear_mezcla'),
    path('mezclas/<int:mezcla_id>/continuar/', views.continuar_mezcla, name='continuar_mezcla'),
    path('mezclas/<int:pk>/', views.detalle_mezcla, name='detalle_mezcla'),
    path('mezclas/<int:pk>/editar/', views.editar_mezcla, name='editar_mezcla'),
    path('mezclas/<int:pk>/eliminar/', views.eliminar_mezcla, name='eliminar_mezcla'),
    
    # Cataciones
    path('cataciones/', views.lista_cataciones, name='lista_cataciones'),
    path('cataciones/crear/', views.crear_catacion, name='crear_catacion'),
    path('cataciones/<int:pk>/', views.detalle_catacion, name='detalle_catacion'),
    path('cataciones/<int:pk>/eliminar/', views.eliminar_catacion, name='eliminar_catacion'),
    path('cataciones/<int:pk>/imprimir/', views.imprimir_catacion, name='imprimir_catacion'),

    # Compradores/Proveedores y Compras
    path('compradores/', views.lista_compradores, name='lista_compradores'),
    path('compradores/', views.lista_compradores, name='lista_proveedores'),  # Alias
    path('compradores/crear/', views.crear_comprador, name='crear_comprador'),
    path('compradores/crear/', views.crear_comprador, name='crear_proveedor'),  # Alias
    path('compradores/comparar/', views.comparar_compradores, name='comparar_compradores'),
    path('compradores/comparar/', views.comparar_compradores, name='comparar_proveedores'),  # Alias
    path('compradores/<int:pk>/', views.detalle_comprador, name='detalle_comprador'),
    path('compradores/<int:pk>/', views.detalle_comprador, name='detalle_proveedor'),  # Alias
    path('compradores/<int:pk>/editar/', views.editar_comprador, name='editar_comprador'),
    path('compradores/<int:pk>/editar/', views.editar_comprador, name='editar_proveedor'),  # Alias
    path('compradores/<int:pk>/eliminar/', views.eliminar_comprador, name='eliminar_comprador'),
    path('compradores/<int:pk>/eliminar/', views.eliminar_comprador, name='eliminar_proveedor'),  # Alias

    # Compras
    path('compras/', views.lista_compras, name='lista_compras'),
    path('compradores/<int:pk>/compras/agregar/', views.agregar_compra, name='agregar_compra'),
    path('compras/<int:pk>/editar/', views.editar_compra, name='editar_compra'),
    path('compras/<int:pk>/eliminar/', views.eliminar_compra, name='eliminar_compra'),

    # Mantenimiento de Planta
    path('mantenimiento/', views.control_mantenimiento, name='control_mantenimiento'),
    path('mantenimiento/realizar/', views.realizar_mantenimiento, name='realizar_mantenimiento'),
    path('mantenimiento/historial/', views.historial_mantenimiento, name='historial_mantenimiento'),

    # Recibos de Café
    path('lotes/<int:lote_id>/recibos/agregar/', views.agregar_recibo, name='agregar_recibo'),
    path('recibos/<int:pk>/editar/', views.editar_recibo, name='editar_recibo'),
    path('recibos/<int:pk>/eliminar/', views.eliminar_recibo, name='eliminar_recibo'),
    path('recibos/<int:recibo_id>/procesar/', views.procesar_desde_recibo, name='procesar_desde_recibo'),

     # ========== EVENTOS ==========
    path('eventos/', views.eventos_lista, name='eventos_lista'),
    
    # Ventas
    path('eventos/venta/crear/<str:tipo_producto>/<int:producto_id>/', views.venta_crear, name='venta_crear'),
    path('eventos/venta/<int:venta_id>/', views.venta_detalle, name='venta_detalle'),
    path('eventos/ventas/', views.ventas_lista, name='ventas_lista'),
    
    # Exportaciones
    path('eventos/exportacion/crear/<str:tipo_producto>/<int:producto_id>/', views.exportacion_crear, name='exportacion_crear'),
    path('eventos/exportacion/<int:exportacion_id>/', views.exportacion_detalle, name='exportacion_detalle'),
    path('eventos/exportaciones/', views.exportaciones_lista, name='exportaciones_lista'),

     # Resumen
    path('resumen-beneficio/', views.resumen_beneficio, name='resumen_beneficio'),


    # Lista de partidas
    path('partidas/', views.lista_partidas, name='lista_partidas'),
    path('partidas/crear/', views.crear_partida, name='crear_partida'),
    path('partidas/<int:pk>/', views.detalle_partida, name='detalle_partida'),
    path('partidas/<int:pk>/editar/', views.editar_partida, name='editar_partida'),
    path('partidas/<int:pk>/eliminar/', views.eliminar_partida, name='eliminar_partida'),

    # SUB-PARTIDAS
    path('partidas/<int:partida_id>/agregar/', views.agregar_subpartida, name='agregar_subpartida'),
    path('subpartidas/<int:pk>/', views.detalle_subpartida, name='detalle_subpartida'),
    path('subpartidas/<int:pk>/editar/', views.editar_subpartida, name='editar_subpartida'),
    path('subpartidas/<int:pk>/eliminar/', views.eliminar_subpartida, name='eliminar_subpartida'),

    # MOVIMIENTOS DE SUBPARTIDA (Trazabilidad de Inventario)
    path('subpartidas/<int:pk>/procesar/', views.procesar_subpartida, name='procesar_subpartida'),
    path('movimientos/<int:pk>/eliminar/', views.eliminar_movimiento, name='eliminar_movimiento'),

    # ========== BENEFICIADO FINCA (Solo Administradores) ==========
    # Trabajadores
    path('beneficiado-finca/trabajadores/', views.lista_trabajadores_view, name='lista_trabajadores'),
    path('beneficiado-finca/trabajadores/crear/', views.crear_trabajador_view, name='crear_trabajador'),
    path('beneficiado-finca/trabajadores/<int:pk>/editar/', views.editar_trabajador_view, name='editar_trabajador'),
    path('beneficiado-finca/trabajadores/<int:pk>/eliminar/', views.eliminar_trabajador_view, name='eliminar_trabajador'),

    # Planillas Semanales
    path('beneficiado-finca/planillas/', views.lista_planillas_view, name='lista_planillas'),
    path('beneficiado-finca/planillas/crear/', views.crear_planilla_view, name='crear_planilla'),
    path('beneficiado-finca/planillas/<int:pk>/', views.detalle_planilla_view, name='detalle_planilla'),
    path('beneficiado-finca/planillas/<int:pk>/editar/', views.editar_planilla_view, name='editar_planilla'),
    path('beneficiado-finca/planillas/<int:pk>/eliminar/', views.eliminar_planilla_view, name='eliminar_planilla'),

    # Registros Diarios
    path('beneficiado-finca/planillas/<int:planilla_id>/registros/agregar/', views.agregar_registro_view, name='agregar_registro'),
    path('beneficiado-finca/registros/<int:pk>/eliminar/', views.eliminar_registro_view, name='eliminar_registro'),

]