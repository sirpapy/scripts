from django import template


register = template.Library()


@register.inclusion_tag("portal/partials/status_badge.html")
def status_badge(status):
    return {
        "status": status,
        "is_error": status in {"error", "error_deleting"},
    }


@register.simple_tag(takes_context=True)
def active_nav(context, url_name):
    current_name = context["request"].resolver_match.url_name
    return "active" if current_name == url_name else ""


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
