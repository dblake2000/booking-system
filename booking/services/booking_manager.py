"""
booking_manager.py
------------------
Coordinates booking creation and cancellation.

Alignment:
- SRS 1.0 Client Self-Booking
- SRS 3.0 Appointment Cancellation (2-hour cutoff)
- SRS 7.0 Double-booking prevention (via AvailabilityEngine)
- SDS BookingManager orchestration

Notes:
- Uses AvailabilityEngine.is_slot_available_for_staff (correct method name).
- Keeps it 100% free and simple (no external services).
"""

from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from ..models import Booking
from .availability_engine import AvailabilityEngine


class BookingManager:
    def __init__(self):
        self.availability = AvailabilityEngine()

    @transaction.atomic
    def create_booking(self, client, service, staff, start_time, notes=""):
        """
        Create a booking after checking for overlap.

        Args:
            client: ClientProfile instance
            service: Service instance (needs duration_minutes)
            staff: Staff instance (can be None if TBA)
            start_time: aware datetime
            notes: optional string

        Raises:
            ValueError: if slot overlaps with an existing booking for that staff.
        """
        # Only check overlap if a staff member is selected
        if staff is not None:
            ok = self.availability.is_slot_available_for_staff(
                staff=staff, service=service, start_time=start_time
            )
            if not ok:
                raise ValueError(
                    "Selected time overlaps with an existing booking for this staff."
                )

        booking = Booking.objects.create(
            client=client,
            service=service,
            staff=staff,
            start_time=start_time,
            notes=notes,
        )
        return booking

    @transaction.atomic
    def cancel_booking(self, booking, cutoff_minutes: int = 120) -> bool:
        """
        Cancel a booking if outside the cutoff window.
        If Booking.status exists, set to CANCELLED; otherwise delete.
        """
        now = timezone.now()
        if booking.start_time - now <= timedelta(minutes=cutoff_minutes):
            raise ValueError("Cannot cancel within 2 hours of appointment start.")

        # If the model has a 'status' field, use it.
        if hasattr(booking, "status"):
            booking.status = "CANCELLED"
            booking.save(update_fields=["status"])
            return True

        # Fallback: delete if status doesn't exist (older version)
        booking.delete()
        return True