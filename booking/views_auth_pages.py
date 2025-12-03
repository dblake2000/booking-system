# booking/views_auth_pages.py
from django.views.generic import TemplateView


class ClientLoginPage(TemplateView):
    """
    Simple client login HTML. Uses /api/auth/login behind the scenes (AJAX).
    Template: templates/login.html
    """
    template_name = "login.html"