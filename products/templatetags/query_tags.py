from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    Outputs the current query string with specified params added,
    updated, or removed (pass None to remove).
    Always resets page to 1 when a filter changes.

    Usage:
        ?{% querystring page=3 %}               → keeps all params, sets page=3
        ?{% querystring sort='price_asc' %}      → keeps all params, sets sort
        ?{% querystring q=None %}                → removes q, keeps the rest
    """
    request = context['request']
    params  = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = str(value)
    # reset to page 1 whenever anything other than 'page' changes
    if list(kwargs.keys()) != ['page']:
        params.pop('page', None)
    return params.urlencode()

@register.simple_tag
def star_pct(rating):
    """Converts a 0–5 rating to a percentage for CSS star-fill width."""
    if not rating:
        return 0
    return round(float(rating) / 5 * 100, 1)

@register.filter
def get_item(dictionary, key):
    """Usage: {{ mydict|get_item:key }}"""
    try:
        return dictionary.get(int(key), 0)
    except (ValueError, AttributeError):
        return dictionary.get(key, 0)