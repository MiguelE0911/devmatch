from django import template
from django.urls import resolve

register = template.Library()


@register.simple_tag(takes_context=True)
def active_link(context, url_name, css_class="text-indigo-600 font-semibold"):
    """
    Devuelve `css_class` si `url_name` (ej. "core:home") corresponde a la
    vista actual. Pensado para templates/partials/navbar.html, que es
    compartido por todo el equipo:

        <a href="{% url 'core:home' %}" class="{% active_link 'core:home' %}">Inicio</a>
    """
    request = context.get("request")
    if request is None:
        return ""
    try:
        current = resolve(request.path_info)
        current_name = f"{current.namespace}:{current.url_name}" if current.namespace else current.url_name
    except Exception:
        return ""
    return css_class if current_name == url_name else ""