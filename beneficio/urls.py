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
    path('procesados/<int:pk>/continuar/', views.continuar_procesado, name='continuar_procesado'),
    
    # Reprocesos
    path('reprocesos/', views.lista_reprocesos, name='lista_reprocesos'),
    path('reprocesos/<int:pk>/', views.detalle_reproceso, name='detalle_reproceso'),
    path('reprocesos/<int:pk>/editar/', views.editar_reproceso, name='editar_reproceso'),
    path('reprocesos/<int:pk>/reprocesar/', views.reprocesar_reproceso, name='reprocesar_reproceso'),
    path('procesados/<int:procesado_id>/reprocesar/', views.crear_reproceso, name='crear_reproceso'),
    
    # Mezclas
    path('mezclas/', views.lista_mezclas, name='lista_mezclas'),
    path('mezclas/crear/', views.crear_mezcla, name='crear_mezcla'),
    path('mezclas/<int:pk>/', views.detalle_mezcla, name='detalle_mezcla'),
    path('mezclas/<int:pk>/editar/', views.editar_mezcla, name='editar_mezcla'),
    path('mezclas/<int:pk>/eliminar/', views.eliminar_mezcla, name='eliminar_mezcla'),
    
    # Cataciones
    path('cataciones/', views.lista_cataciones, name='lista_cataciones'),
    path('cataciones/crear/', views.crear_catacion, name='crear_catacion'),
    path('cataciones/<int:pk>/', views.detalle_catacion, name='detalle_catacion'),
    path('cataciones/<int:pk>/eliminar/', views.eliminar_catacion, name='eliminar_catacion'),
    path('cataciones/<int:pk>/imprimir/', views.imprimir_catacion, name='imprimir_catacion'),
]