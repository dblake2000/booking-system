# booking/views.py
#
# Purpose:
# - CRUD APIs for Clients, Services, Staff, Bookings, and Feedback.
# - Availability endpoint (SRS 7.0) with robust date parsing.
# - Email confirmations/cancellations (SRS 6.0, SRS 3.0).
# - Permissions:
#   * Service writes are staff-only (price updates, activate/deactivate).
#   * Booking creation requires NO login. Public flow: create client -> create booking.
#
# Change log (2025-12-03):
# - On successful booking creation, set status="confirmed" and save.
#   This triggers the notifications.signals.post_save hook to send the
#   confirmation email using Django's email backend configured in settings.
#
import re
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import ClientProfile, Service, Staff, Booking, Feedback
from .serializers import (
    ClientProfileSerializer,
    ServiceSerializer,
    StaffSerializer,
    BookingSerializer,
    FeedbackSerializer,
)
from .services.booking_manager import BookingManager
from .services.notification_service import NotificationService  # legacy console helper
from .services.availability_engine import AvailabilityEngine  # computes open slots

PHONE_RE = re.compile(r"^\d{7,15}$")


# -------------------- Permissions --------------------
class IsStaffOrReadOnly(BasePermission):
    """
    Read: anyone
    Write: staff only
    """
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return bool(request.user and request.user.is_staff)


# -------------------- ViewSets --------------------
class ClientProfileViewSet(viewsets.ModelViewSet):
    queryset = ClientProfile.objects.all().order_by("id")
    serializer_class = ClientProfileSerializer

    def create(self, request, *args, **kwargs):
        """
        Create ClientProfile with basic validation for name/email/phone.
        Phone must be 7–15 digits (digits only).
        """
        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()
        phone = (request.data.get("phone") or "").strip()

        if not name or not email or not phone:
            return Response({"detail": "name, email, and phone are required."}, status=400)

        if not PHONE_RE.match(phone):
            return Response(
                {"detail": "Phone must be digits only, 7 to 15 digits."},
                status=400,
            )

        serializer = self.get_serializer(data={"name": name, "email": email, "phone": phone})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)


class ServiceViewSet(viewsets.ModelViewSet):
    """
    Service catalog:
    - Anyone can list active services.
    - Only staff can create/update/delete services (IsStaffOrReadOnly).
    - Price updates are logged into PriceHistory in perform_update.
    """
    serializer_class = ServiceSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        """
        Staff can see all services; public sees only active services.
        """
        user = getattr(self.request, "user", None)
        qs = Service.objects.all().order_by("id")
        if user and user.is_authenticated and user.is_staff:
            return qs
        return qs.filter(active=True)

    def perform_update(self, serializer):
        """
        Log price changes when a service is updated (SRS 5.0 price management).
        """
        service = self.get_object()
        old_price = service.price
        instance = serializer.save()
        if "price" in serializer.validated_data and instance.price != old_price:
            from .models import PriceHistory
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

    Public booking flow (no login):
    - Create a ClientProfile (name/email/phone), then create a booking.
    """
    queryset = Booking.objects.all().order_by("-start_time")
    serializer_class = BookingSerializer
    manager = BookingManager()
    notifier = NotificationService()  # legacy console notifier (kept for cancel)

    def create(self, request, *args, **kwargs):
        """
        Create a booking with validated payload:
        - Requires: client (ClientProfile PK), service (PK), start_time (ISO).
        - Optional: staff (PK), notes (str).
        - Blocks inactive services.
        - IMPORTANT: After creating the booking, immediately set status to "confirmed"
          and save. This triggers notifications.signals.post_save to send a
          real email confirmation to the client's email address using the configured
          EMAIL_BACKEND.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = data["client"]
        service = data["service"]
        staff = data.get("staff")
        start_time = data["start_time"]
        notes = data.get("notes", "")

        # Block inactive services (safer for public API)
        if hasattr(service, "active") and not service.active:
            return Response(
                {"detail": "This service is not currently available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create booking via domain manager to keep logic centralized
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

        # Immediately confirm booking so the post_save signal sends the email.
        # The signal handler lives in notifications/signals.py and will:
        # - Compose a professional confirmation message
        # - Send an email to booking.client.email
        # - Create a Notification record
        if getattr(booking, "status", None) != "confirmed":
            booking.status = "confirmed"
            # Save only the field that changed to avoid redundant writes
            booking.save(update_fields=["status"])

        # Note: Leaving legacy console confirmation call in place is optional.
        # It can be removed if redundant with real email sending via signal.
        # self.notifier.send_confirmation(booking)

        # Re-serialize to include updated status
        out = BookingSerializer(booking)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancel a booking (public). Respects 2-hour cutoff.
        On success, sends a cancellation notification (legacy console notifier retained).
        """
        booking = get_object_or_404(Booking, pk=pk)

        # capture before cancellation (for email/notification if needed)
        snapshot = {
            "id": booking.id,
            "client_email": booking.client.email,
            "start_time": booking.start_time,
        }

        try:
            self.manager.cancel_booking(booking, cutoff_minutes=120)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Existing console cancellation (can be upgraded to real email later)
        self.notifier.send_cancellation(snapshot)
        return Response({"detail": "Booking cancelled."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        """
        GET /api/bookings/availability/?service=ID&date=YYYY-MM-DD
        Also accepts inputs that include time; we trim to the date part.
        Filters out past slots relative to current timezone.
        """
        service_id = (request.query_params.get("service") or "").strip()
        date_raw = (request.query_params.get("date") or "").strip()

        if not service_id or not date_raw:
            return Response(
                {"detail": "Missing 'service' or 'date'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Normalize to 'YYYY-MM-DD'
        if "T" in date_raw:
            date_str = date_raw.split("T", 1)[0].strip()
        elif " " in date_raw:
            date_str = date_raw.split(" ", 1)[0].strip()
        else:
            date_str = date_raw

        # Validate date format
        d = parse_date(date_str)
        if d is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve service or 404
        service = get_object_or_404(Service, pk=service_id)

        # Convert date to TZ-aware day start
        from .services.slot_utils import date_to_range
        try:
            day_start, _day_end = date_to_range(date_str)
        except Exception:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Compute availability
        engine = AvailabilityEngine()
        staff_qs = Staff.objects.all().order_by("id")
        data = engine.find_available_slots(service, day_start, staff_qs)

        # Filter out past slots (today)
        tz = timezone.get_current_timezone()
        now = timezone.now()
        filtered = []
        for s in data["slots"]:
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