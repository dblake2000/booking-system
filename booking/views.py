## booking/views.py
#
# Purpose:
# - CRUD APIs for Clients, Services, Staff, and Bookings.
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
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import ClientProfile, Service, Staff, Booking
from .serializers import (
    ClientProfileSerializer,
    ServiceSerializer,
    StaffSerializer,
    BookingSerializer,
)

from .services.booking_manager import BookingManager
from .services.notification_service import NotificationService 	# console email (FREE)
from .services.availability_engine import AvailabilityEngine 	# computes open slots


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
    queryset = Service.objects.all().order_by("id")
    serializer_class = ServiceSerializer
    
    @action(detail=False, methods=["get"], url_path="all")
    def all_services(self, request):
        """
        Staff-only endpoint to list ALL services (including inactive ones).
        Feature 6.0: Price Management - allows staff to see and manage all services.
        
        GET /api/services/all/
        
        Returns:
            Response: List of all services with complete details
        """
        from rest_framework.permissions import IsAuthenticated
        
        # Check authentication
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check staff permission
        if not request.user.is_staff:
            return Response(
                {"detail": "Staff privileges required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Return all services (not just active ones)
        all_services = Service.objects.all().order_by("id")
        serializer = ServiceSerializer(all_services, many=True)
        
        return Response(serializer.data)


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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = data["client"] 			# PK -> instance
        service = data["service"]
        staff = data.get("staff") 			# optional
        start_time = data["start_time"]
        notes = data.get("notes", "")

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
        booking = get_object_or_404(Booking, pk=pk)

        # capture before delete
        snapshot = {
            "id": booking.id,
            "client_email": booking.client.email,
            "start_time": booking.start_time,
        }

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