# booking/views.py
#
# Purpose:
# - CRUD APIs for Clients, Services, Staff, and Bookings.
# - Availability endpoint (SRS 7.0) with robust date parsing.
# - Console "emails" for confirmations/cancellations (FREE) (SRS 6.0, SRS 3.0).

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import ClientProfile, Service, Staff, Booking, Feedback
from .serializers import (
    ClientProfileSerializer,
    ServiceSerializer,
    StaffSerializer,
    BookingSerializer,
    FeedbackSerializer
)

from .services.booking_manager import BookingManager
from .services.notification_service import NotificationService  # console email (FREE)
from .services.availability_engine import AvailabilityEngine  # computes open slots


# ---- Helpers (local) ---------------------------------------------------------

def _extract_date_only(date_str: str) -> str:
    """
    Accept common formats and return just the YYYY-MM-DD part.

    Accepts:
      - 'YYYY-MM-DD'
      - 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DDTHH:MM:SS' (optional 'Z' or offset)
      - 'YYYY-MM-DD HH:MM' (space)
    """
    if not date_str:
        return date_str
    # Split on 'T' or space to drop any time part
    if "T" in date_str:
        date_str = date_str.split("T", 1)[0]
    if " " in date_str:
        date_str = date_str.split(" ", 1)[0]
    return date_str


# ---- ViewSets ----------------------------------------------------------------

class ClientProfileViewSet(viewsets.ModelViewSet):
    queryset = ClientProfile.objects.all().order_by("id")
    serializer_class = ClientProfileSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        # Only show active services by default (catalog)
        return Service.objects.filter(active=True).order_by("id")
    
    # Log price changes when a service is updated (optional SRS 5.0 price history)
    def perform_update(self, serializer):
        service = self.get_object()
        old_price = service.price
        instance = serializer.save()
        # If price is provided and changed, write a history row
        if "price" in serializer.validated_data and instance.price != old_price:
            from .models import PriceHistory  # ensure PriceHistory exists in your models
            PriceHistory.objects.create(
                service=instance,
                old_price=old_price,
                new_price=instance.price,
            )


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by("id")
    serializer_class = StaffSerializer


class BookingViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - POST   /api/bookings/                   create (SRS 1.0, 6.0, 7.0)
    - POST   /api/bookings/{id}/cancel/       cancel with 2h cutoff (SRS 3.0)
    - GET    /api/bookings/availability/      availability (SRS 7.0)
    """
    queryset = Booking.objects.all().order_by("-start_time")
    serializer_class = BookingSerializer

    manager = BookingManager()
    notifier = NotificationService()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = data["client"]
        service = data["service"]
        staff = data.get("staff")
        start_time = data["start_time"]
        notes = data.get("notes", "")

        if hasattr(service, "active") and not service.active:
            return Response(
                {"detail": "This service is not currently available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = self.manager.create_booking(
                client=client,
                service=service,
                staff=staff,
                start_time=start_time,
                notes=notes,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # SRS 6.0: confirmation to console
        self.notifier.send_confirmation(booking)

        out = BookingSerializer(booking)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = get_object_or_404(Booking, pk=pk)

        # capture before delete
        snapshot = {
            "id": booking.id,
            "client_email": booking.client.email,
            "start_time": booking.start_time,
        }

        try:
            self.manager.cancel_booking(booking, cutoff_minutes=120)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        self.notifier.send_cancellation(snapshot)
        return Response({"detail": "Booking cancelled."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        """
        GET /api/bookings/availability/?service=ID&date=YYYY-MM-DD
        Also accepts:
          - date=YYYY-MM-DDTHH:MM[:SS][Z]
          - date=YYYY-MM-DD HH:MM[:SS]
        """
        service_id = request.query_params.get("service")
        date_raw = request.query_params.get("date")

        if not service_id or not date_raw:
            return Response(
                {"detail": "Missing 'service' or 'date'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Be forgiving with date formats
        date_str = _extract_date_only(date_raw)

        service = get_object_or_404(Service, pk=service_id)

        from .services.slot_utils import date_to_range
        try:
            day_start, _day_end = date_to_range(date_str)
        except Exception:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        engine = AvailabilityEngine()
        staff_qs = Staff.objects.all().order_by("id")

        data = engine.find_available_slots(service, day_start, staff_qs)

        # Filter out past slots if querying today
        tz = timezone.get_current_timezone()
        now = timezone.now()
        filtered = []
        for s in data["slots"]:
            # robust parse for ISO; handle naive by localizing
            start_dt = timezone.datetime.fromisoformat(s["start_time"])
            if start_dt.tzinfo is None:
                start_dt = tz.localize(start_dt)
            else:
                start_dt = start_dt.astimezone(tz)
            if start_dt > now:
                filtered.append(s)

        return Response({"slots": filtered})
    
class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all().order_by("-created_at")
    serializer_class = FeedbackSerializer