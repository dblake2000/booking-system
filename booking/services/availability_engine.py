"""
availability_engine.py
----------------------
Computes availability by checking candidate time slots against:
1) existing bookings (double-booking prevention), and
2) optional staff availability windows (if defined).

Defensive checks:
- Skip any 'staff' that isn't a booking.models.Staff instance to avoid
  'Cannot query "<name>": Must be "Staff" instance' errors.

Change log (2025-12-03):
- _has_booking_conflict now uses symmetric overlap detection:
  existing_start < new_end AND existing_end > new_start
  to avoid missed overlaps or false negatives.
"""

from datetime import timedelta
from django.db.models import Q
from ..models import Booking, Staff  # IMPORTANT: booking.models.Staff

# Optional import: staff availability windows
try:
    from staff.models import StaffAvailability
    HAS_STAFF_AVAILABILITY = True
except Exception:
    StaffAvailability = None
    HAS_STAFF_AVAILABILITY = False


class AvailabilityEngine:
    def _is_valid_staff(self, staff) -> bool:
        return isinstance(staff, Staff)

    def _has_booking_conflict(self, staff, start_time, duration_minutes: int) -> bool:
        """
        Robust overlap check:
        Conflict if any existing booking for 'staff' satisfies:
            existing_start < new_end AND existing_end > new_start
        where existing_end = existing_start + existing.service.duration_minutes
        """
        if not self._is_valid_staff(staff):
            return True  # treat as conflict; skip invalid values

        new_start = start_time
        new_end = start_time + timedelta(minutes=duration_minutes)

        # Compute overlaps in Python (portable and clear)
        for b in Booking.objects.filter(staff=staff).select_related("service"):
            existing_start = b.start_time
            existing_end = b.start_time + timedelta(minutes=b.service.duration_minutes)
            if existing_start < new_end and existing_end > new_start:
                return True
        return False

    def _fits_staff_availability(self, staff, start_time, duration_minutes: int) -> bool:
        if not HAS_STAFF_AVAILABILITY:
            return True
        if not self._is_valid_staff(staff):
            return False

        duration = timedelta(minutes=duration_minutes)
        end_time = start_time + duration

        qs = StaffAvailability.objects.filter(
            staff=staff,
            start_time__lte=start_time,
            end_time__gte=end_time,
        )
        if qs.exists():
            return True

        # If this staff has no availability rows at all, allow by default (demo-friendly).
        return not StaffAvailability.objects.filter(staff=staff).exists()

    def is_slot_available_for_staff(self, staff, service, start_time) -> bool:
        if self._has_booking_conflict(staff, start_time, service.duration_minutes):
            return False
        if not self._fits_staff_availability(staff, start_time, service.duration_minutes):
            return False
        return True

    def find_available_slots(self, service, date_start, staff_queryset):
        from .slot_utils import generate_slots_for_day

        # DEBUG — uncomment to inspect the staff list
        # print("DEBUG staff values:", [
        #      (getattr(s, "id", None), getattr(s, "name", None), type(s))
        #      for s in staff_queryset
        #  ])

        slots = generate_slots_for_day(
            service_duration_minutes=service.duration_minutes,
            date_start=date_start,
        )

        results = []
        for start in slots:
            free_staff_ids = []
            for staff in staff_queryset:
                if not self._is_valid_staff(staff):
                    continue  # skip bad values
                if self.is_slot_available_for_staff(staff, service, start):
                    free_staff_ids.append(staff.id)
            if free_staff_ids:
                results.append({"start_time": start.isoformat(), "staff_ids": free_staff_ids})

        return {"slots": results}