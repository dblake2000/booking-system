## booking/views.py
#
# Purpose:
# - CRUD APIs for Clients, Services, Staff, Bookings, and Feedback.
# - Availability endpoint (SRS 7.0) with robust date parsing.
# - Console "emails" for confirmations/cancellations (FREE) (SRS 6.0, SRS 3.0).
# - Permissions:
#   * Service writes are staff-only (price updates, activate/deactivate).
#   * Booking creation requires NO login. Public flow: create client -> create booking.

from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail # Kept for existing dependencies, though staff cancel is now signal-based
from django.conf import settings # Needed for staff cancel return (uses EMAIL_HOST_USER)

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
from .services.notification_service import NotificationService 	# console email (FREE)
from .services.availability_engine import AvailabilityEngine 	# computes open slots


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
        # Staff can see all; public sees only active
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
    - POST 	/api/bookings/ 	 	 	 	 	 create (SRS 1.0, 6.0, 7.0)
    - POST 	/api/bookings/{id}/cancel/ 	 	 	 Staff cancel (relies on signal)
    - POST 	/api/bookings/client_cancel/        Client self-cancel (NEW)
    - GET 	/api/bookings/availability/ 	 	 availability (SRS 7.0)

    Public booking flow:
    - NO login required. Clients can create a ClientProfile (name/email) then book.
    """
    queryset = Booking.objects.all().order_by("-start_time")
    serializer_class = BookingSerializer
    manager = BookingManager()
    notifier = NotificationService()

    def create(self, request, *args, **kwargs):
        """
        Create a booking:
        - No login required.
        - Expects client (ClientProfile id), service id, optional staff id, start_time (ISO).
        - Blocks inactive services.
        - Sends confirmation (console) on success.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = data["client"] 			# PK -> instance
        service = data["service"]
        staff = data.get("staff") 			# optional
        start_time = data["start_time"]
        notes = data.get("notes", "")

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

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Staff/Admin action to cancel a specific booking.
        The save() triggers the post_save signal which handles all notifications.
        """
        try:
            booking = self.get_object() # Fetches the Booking instance
        except Exception:
            return Response(
                {"detail": "Booking not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Validation
        if booking.status == "CANCELLED":
            return Response(
                {"detail": "Booking is already cancelled."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update Model Fields
        booking.status = "CANCELLED"
        booking.cancellation_time = timezone.now()
        
        # This triggers the post_save signal in booking/signals.py which sends the necessary cancellation emails to client and admin.
        booking.save(update_fields=['status', 'cancellation_time'])

        # Return API Response
        return Response(
            {"detail": "Booking cancelled successfully by staff. Notifications processed by signal.", 
             "new_status": booking.status},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], url_path='client_cancel')
    def client_cancel(self, request):
        """
        NEW: Allows an unauthenticated client to cancel a booking by providing 
        the Booking ID (pk) and their verified Email.
        """
        test_number = 2
        booking_id = request.data.get('booking_id')
        client_email = request.data.get('client_email')

        # Input Validation
        if not booking_id or not client_email:
            return Response(
                {"detail": "Both Booking ID and Email are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Look up the booking by ID
            booking = get_object_or_404(Booking, pk=booking_id)
        except Exception:
            return Response(
                {"detail": "Cancellation failed. Please check your details or call the business at " 
                           f"{test_number}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        #Do checks to see if the provided email matches the client's email
        if booking.client.email.lower() != client_email.lower():
            return Response(
                {"detail": "Cancellation failed. The provided email does not match the booking record."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Status Validation
        if booking.status in ["CANCELLED", "COMPLETED"]:
            return Response(
                {"detail": f"Booking #{booking_id} is already in the {booking.status} state."},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = "CANCELLED"
        booking.cancellation_time = timezone.now()
        booking.save(update_fields=['status', 'cancellation_time'])

        # Return Success Message
        success_message = (
            f"Booking #{booking_id} has been successfully CANCELLED. "
            "You will receive an email confirmation shortly. "
            "If you did not make this cancellation or believe it was a mistake, "
            f"please call us immediately at {test_number}."
        )

        return Response({"detail": success_message}, status=status.HTTP_200_OK)


    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        """
        GET /api/bookings/availability/?service=ID&date=YYYY-MM-DD
        Also accepts inputs that include time; we trim to the date part.
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

        # Validate
        d = parse_date(date_str)
        if d is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve service
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