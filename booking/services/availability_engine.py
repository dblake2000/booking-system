"""
availability_engine.py
----------------------
Computes availability by checking candidate time slots against:
1) existing bookings (to prevent double-booking), and
2) optional staff availability windows (if defined).

Alignment with SRS/SDS:
- SRS 7.0 Date & Time Selection:
  * Only show valid (free) time slots.
  * Prevent double-booking.
  * Past-time filtering is done in the view layer (BookingViewSet.availability).
- SDS:
  * AvailabilityEngine evaluates conflicts.
  * Integrates business hours (via slot_utils) and StaffAvailability windows.

Beginner notes:
- If you haven't added any StaffAvailability rows, this engine will treat staff
  as available by default (so your demo still works).
- If you add StaffAvailability rows for a staff member, the slot must fit
  inside at least one of that staff member's availability windows.
"""

from datetime import timedelta
from django.db.models import Q

from ..models import Booking, Staff

# Optional import: if staff availability exists, we'll use it.
try:
    from staff.models import StaffAvailability  # defined in staff/models.py
    HAS_STAFF_AVAILABILITY = True
except Exception:
    # If staff app or model isn't ready, we gracefully skip this feature.
    StaffAvailability = None
    HAS_STAFF_AVAILABILITY = False


class AvailabilityEngine:
    """
    Provides methods to:
    - Check if a given staff member is free for a specific start time.
    - Build a list of available slots for a day by checking all staff.
    """

    def _fits_staff_availability(self, staff: Staff, start_time, duration_minutes: int) -> bool:
        """
        If StaffAvailability rows exist for this staff, the slot must be fully
        contained within at least one availability window.

        If there are NO availability rows for this staff:
          - We treat staff as available by default (easy for demos).
          - You can change this policy later to "not available unless defined".
        """
        if not HAS_STAFF_AVAILABILITY:
            return True  # feature not active; allow

        duration = timedelta(minutes=duration_minutes)
        end_time = start_time + duration

        # All windows that fully cover the [start_time, end_time) interval
        qs = StaffAvailability.objects.filter(
            staff=staff,
            start_time__lte=start_time,
            end_time__gte=end_time,
        )

        if qs.exists():
            return True

        # If the staff has zero availability rows at all, allow by default
        if not StaffAvailability.objects.filter(staff=staff).exists():
            return True

        # Otherwise, availability rows exist but none cover this slot -> not available
        return False

    def _has_booking_conflict(self, staff: Staff, start_time, duration_minutes: int) -> bool:
        """
        Simple overlap rule (easy to understand):
        - Let D be the service duration.
        - Any booking for the same staff with start_time in [start_time - D, start_time + D)
          is treated as overlapping for our student project purposes.
        """
        duration = timedelta(minutes=duration_minutes)
        end_time = start_time + duration

        return Booking.objects.filter(staff=staff).filter(
            Q(start_time__lt=end_time) & Q(start_time__gte=start_time - duration)
        ).exists()

    def is_slot_available_for_staff(self, staff: Staff, service, start_time) -> bool:
        """
        A staff member is available for a slot if:
        - The slot does NOT conflict with existing bookings, AND
        - (If StaffAvailability windows exist) the slot fits inside one window.
        """
        # 1) Check conflicts with existing bookings
        if self._has_booking_conflict(staff, start_time, service.duration_minutes):
            return False

        # 2) Check staff availability windows (if feature is active)
        if not self._fits_staff_availability(staff, start_time, service.duration_minutes):
            return False

        return True

    def find_available_slots(self, service, date_start, staff_queryset):
        """
        Build a list of candidate slot starts across business hours (from slot_utils),
        then include only slots where at least one staff member is free.

        Returns:
            dict: { "slots": [ { "start_time": ISO8601, "staff_ids": [1,2,...] }, ... ] }
        """
        from .slot_utils import generate_slots_for_day

        # Candidate starts across business hours (BUSINESS_OPEN/CLOSE or defaults)
        slots = generate_slots_for_day(
            service_duration_minutes=service.duration_minutes,
            date_start=date_start,
        )

        results = []
        for start in slots:
            free_staff_ids = []
            for staff in staff_queryset:
                if self.is_slot_available_for_staff(staff, service, start):
                    free_staff_ids.append(staff.id)

            # Only include the slot if at least one staff is free
            if free_staff_ids:
                results.append({"start_time": start.isoformat(), "staff_ids": free_staff_ids})

        return {"slots": results}