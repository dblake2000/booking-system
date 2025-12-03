from django.views.generic import TemplateView

class BookingDemoView(TemplateView):
    template_name = "booking.html"