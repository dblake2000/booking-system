# reports/views.py

from django.db.models import Count
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission

from booking.models import Booking, Service


class IsStaffOnly(BasePermission):
    """
    Only allow requests from logged-in staff users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class ReportsView(APIView):
    """
    GET /api/reports/summary

    Returns JSON with:
    - bookings_per_day: [{ "day": "YYYY-MM-DD", "count": N }, ...]
    - cancellations_per_day: [{ "day": "YYYY-MM-DD", "count": N }, ...]
    - top_services: [{ "service_id": X, "service_name": "...", "count": N }, ...]

    Only accessible by staff users.
    """
    permission_classes = [IsStaffOnly]

    def get(self, request):
        # Look back 30 days from now
        now = timezone.now()
        start = now - timezone.timedelta(days=30)

        # Bookings per day (last 30 days)
        # .extra(select={'day': "date(start_time)"}) is a simple way to group by date(start_time).
        # This is OK for a student project; more advanced: annotate with TruncDate (PostgreSQL).
        bookings_qs = (
            Booking.objects.filter(start_time__gte=start)
            .extra(select={'day': "date(start_time)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        # Cancellations per day (last 30 days)
        field_names = [f.name for f in Booking._meta.get_fields()]
        if "status" in field_names:
            cancellations_qs = (
                Booking.objects.filter(status="CANCELLED", start_time__gte=start)
                .extra(select={'day': "date(start_time)"})
                .values('day')
                .annotate(count=Count('id'))
                .order_by('day')
            )
        else:
            cancellations_qs = []

        # Top services by bookings (last 30 days), top 5
        top_services = (
            Booking.objects.filter(start_time__gte=start)
            .values('service')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        # Map service IDs to service names for readability
        service_names = {s.id: s.name for s in Service.objects.all()}
        top_services_named = [
            {
                "service_id": row["service"],
                "service_name": service_names.get(row["service"]),
                "count": row["count"],
            }
            for row in top_services
        ]

        data = {
            "bookings_per_day": list(bookings_qs),
            "cancellations_per_day": list(cancellations_qs),
            "top_services": top_services_named,
        }
        return Response(data)