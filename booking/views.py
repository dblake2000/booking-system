# booking/views.py
#
# Purpose:
# - CRUD APIs for Clients, Services, Staff, Bookings, and Feedback.
# - Availability endpoint (SRS 7.0) with robust date parsing.
# - Console "emails" for confirmations/cancellations (FREE) (SRS 6.0, SRS 3.0).
# - Permissions:
#   * Service writes are staff-only (price updates, activate/deactivate).
#   * Clients see/cancel only their own bookings; staff see all.
#   * When a client is logged in, booking creation is forced to their profile.

from datetime import datetime
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import (
    ClientProfile,
    Service,
    Staff,
    Booking,
    Feedback,
)
from .serializers import (
    ClientProfileSerializer,
    ServiceSerializer,
    StaffSerializer,
    BookingSerializer,
    FeedbackSerializer,
)
from .services.booking_manager import BookingManager
from .services.notification_service import NotificationService  # console email (FREE)
from .services.availability_engine import AvailabilityEngine  # computes open slots


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
        # Staff can see all services (active and inactive),
        # non-staff only see active ones (catalog).
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
            # Lazy import to avoid circulars
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

    Permissions:
    - Staff: see all bookings, can cancel any (respecting cutoff).
    - Client: see only own bookings, can cancel only own bookings.
    """
    serializer_class = BookingSerializer
    manager = BookingManager()
    notifier = NotificationService()

    def get_queryset(self):
        qs = Booking.objects.all().order_by("-start_time")
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            # Client sees only their bookings
            if hasattr(user, "client_profile"):
                return qs.filter(client=user.client_profile)
            return qs.none()
        # Staff sees all; anonymous callers typically won’t list
        return qs

    def create(self, request, *args, **kwargs):
        """
        Create a booking:
        - If client user is logged in, force client field to their ClientProfile.
        - Block inactive services.
        - Send confirmation to console on success.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = data["client"]
        service = data["service"]
        staff = data.get("staff")
        start_time = data["start_time"]
        notes = data.get("notes", "")

        # If a client user is logged in, force the booking client to that user’s profile
        user = request.user
        if user.is_authenticated and not user.is_staff:
            if hasattr(user, "client_profile"):
                client = user.client_profile
            else:
                return Response(
                    {"detail": "No client profile linked to this account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Block inactive services
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

        # SRS 6.0: confirmation to console (FREE)
        self.notifier.send_confirmation(booking)

        out = BookingSerializer(booking)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancel a booking:
        - Staff can cancel any booking (respecting cutoff).
        - Client can cancel only their own booking (respecting cutoff).
        """
        booking = get_object_or_404(Booking, pk=pk)

        # Permission: staff OR the client who owns this booking
        user = request.user
        if user.is_authenticated and not user.is_staff:
            if not hasattr(user, "client_profile") or booking.client_id != user.client_profile.id:
                return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        # capture before cancellation (for email)
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
        Also accepts inputs that include time; we trim to the date part.

        Debug: prints the raw and normalized date strings to the server console.
        """
        # 1) Read and trim
        service_id = (request.query_params.get("service") or "").strip()
        date_raw = (request.query_params.get("date") or "").strip()

        if not service_id or not date_raw:
            return Response(
                {"detail": "Missing 'service' or 'date'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) Normalize to 'YYYY-MM-DD'
        if "T" in date_raw:
            date_str = date_raw.split("T", 1)[0].strip()
        elif " " in date_raw:
            date_str = date_raw.split(" ", 1)[0].strip()
        else:
            date_str = date_raw

        # ---------------- DEBUG (safe placement) ----------------
        print(
            "DEBUG availability:",
            "service_id=", repr(service_id),
            "date_raw=", repr(date_raw),
            "date_str=", repr(date_str),
        )
        # --------------------------------------------------------

        # 3) Strictly validate the date
        d = parse_date(date_str)
        if d is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) Resolve service
        service = get_object_or_404(Service, pk=service_id)

        # 5) Convert the date to a TZ-aware day range
        from .services.slot_utils import date_to_range
        try:
            day_start, _day_end = date_to_range(date_str)
        except Exception:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 6) Compute availability
        engine = AvailabilityEngine()
        staff_qs = Staff.objects.all().order_by("id")
        data = engine.find_available_slots(service, day_start, staff_qs)

        # 7) Filter out past slots (today)
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