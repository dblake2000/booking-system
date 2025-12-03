# booking/views_staff_pages.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView


class StaffDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Staff-only HTML page to manage services (pretty UI).
    Must be logged in as staff via /admin.
    Template: templates/staff_dashboard.html
    """
    template_name = "staff_dashboard.html"

    def test_func(self):
        return self.request.user.is_staff