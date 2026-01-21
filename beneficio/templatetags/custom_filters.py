from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter para acceder a items de diccionario usando variables.
    Uso: {{ mi_diccionario|get_item:mi_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter(name='divide')
def divide(value, divisor):
    """
    Divide un valor por un divisor.
    Uso: {{ valor|divide:100 }}
    """
    try:
        return Decimal(str(value)) / Decimal(str(divisor))
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
