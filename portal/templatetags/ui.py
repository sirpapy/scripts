from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


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


class ModalNode(template.Node):
    OPTIONAL_KWARGS = ("kicker", "modal_class", "body_class")

    def __init__(self, nodelist, modal_id, title, kwargs):
        self.nodelist = nodelist
        self.modal_id = modal_id
        self.title = title
        self.kwargs = kwargs

    def render(self, context):
        resolved = {
            key: expr.resolve(context) if expr else ""
            for key, expr in ((name, self.kwargs.get(name)) for name in self.OPTIONAL_KWARGS)
        }

        return render_to_string("portal/partials/modal.html", {
            "modal_id": self.modal_id.resolve(context),
            "title": self.title.resolve(context),
            "body": mark_safe(self.nodelist.render(context)),
            **resolved,
        })


@register.tag
def modal(parser, token):
    """Enveloppe le contenu jusqu'a {% endmodal %} dans la coquille de
    modale partagee (portal/partials/modal.html) - l'equivalent d'un slot
    Vue : on ecrit la coquille une fois, on reutilise avec n'importe quel
    contenu.

    Usage : {% modal "my-modal" title="Titre" kicker="Categorie" %}
              ... contenu, avec acces normal aux variables du contexte ...
            {% endmodal %}

    kicker, modal_class (classe ajoutee sur .modal, ex: pour une largeur
    custom) et body_class (classe ajoutee sur .modal-body) sont optionnels.
    """
    bits = token.split_contents()[1:]

    if not bits:
        raise template.TemplateSyntaxError("{% modal %} attend un id, ex: {% modal \"my-modal\" title=\"...\" %}")

    modal_id = parser.compile_filter(bits[0])
    kwargs = {}

    for bit in bits[1:]:
        key, _, value = bit.partition("=")
        kwargs[key] = parser.compile_filter(value)

    nodelist = parser.parse(("endmodal",))
    parser.delete_first_token()

    return ModalNode(nodelist, modal_id, kwargs["title"], kwargs)
