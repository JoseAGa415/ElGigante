from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import *

class LoteForm(forms.ModelForm):
    """Formulario para crear/editar lotes"""
    class Meta:
        model = Lote
        fields = ['codigo', 'tipo_cafe', 'bodega', 'peso_kg', 'humedad', 
                 'fecha_ingreso', 'proveedor', 'precio_quintal', 'observaciones']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600 focus:border-transparent',
                'placeholder': 'Código único del lote'
            }),
            'tipo_cafe': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600'
            }),
            'bodega': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600'
            }),
            'peso_kg': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Peso en kilogramos'
            }),
            'humedad': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Porcentaje de humedad'
            }),
            'fecha_ingreso': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'type': 'datetime-local'
            }),
            'proveedor': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'placeholder': 'Nombre del proveedor'
            }),
            'precio_quintal': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Precio por quintal'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
        }

class ProcesadoForm(forms.ModelForm):
    """Formulario para crear procesados/trillas"""
    class Meta:
        model = Procesado
        fields = ['lote', 'fecha', 'peso_inicial_kg', 'peso_final_kg', 
                 'catadura', 'rechazo_electronica', 'bajo_zaranda', 'barridos', 'observaciones']
        widgets = {
            'lote': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600'
            }),
            'fecha': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'type': 'datetime-local'
            }),
            'peso_inicial_kg': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Peso inicial en kg'
            }),
            'peso_final_kg': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Peso final en kg'
            }),
            'catadura': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Catadura en kg'
            }),
            'rechazo_electronica': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Rechazo electrónica en kg'
            }),
            'bajo_zaranda': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Bajo zaranda en kg'
            }),
            'barridos': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Barridos en kg'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'rows': 3,
                'placeholder': 'Observaciones del proceso'
            }),
        }

class ReprocesoForm(forms.ModelForm):
    """Formulario para crear reprocesos"""
    class Meta:
        model = Reproceso
        fields = ['fecha', 'peso_inicial_kg', 'peso_final_kg', 
                 'catadura', 'rechazo_electronica', 'bajo_zaranda', 'barridos', 'motivo']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'type': 'datetime-local'
            }),
            'peso_inicial_kg': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Peso inicial en kg'
            }),
            'peso_final_kg': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Peso final en kg'
            }),
            'catadura': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Catadura en kg'
            }),
            'rechazo_electronica': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Rechazo electrónica en kg'
            }),
            'bajo_zaranda': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Bajo zaranda en kg'
            }),
            'barridos': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'step': '0.01',
                'placeholder': 'Barridos en kg'
            }),
            'motivo': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'rows': 3,
                'placeholder': 'Motivo del reproceso'
            }),
        }

class MezclaForm(forms.ModelForm):
    """Formulario para crear mezclas"""
    class Meta:
        model = Mezcla
        fields = ['fecha', 'descripcion', 'destino']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'type': 'datetime-local'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'rows': 3,
                'placeholder': 'Descripción de la mezcla'
            }),
            'destino': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-amber-600',
                'placeholder': 'Destino de la mezcla'
            }),
        }