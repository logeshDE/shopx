from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """Splits a string by argument."""
    if not value:
        return []
    return value.split(arg)
