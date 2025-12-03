"""
availability_engine.py
----------------------
Computes availability by checking candidate time slots against existing bookings.

Alignment with SRS/SDS:
- SRS 7.0 Date & Time Selection:
  * Only show valid (free) time slots.
  * Prevent double-booking.
  * Exclude past-time slots (handled in the view layer).
- SDS Components:
  * AvailabilityEngine evaluates conflicts.
  * Future: integrate StaffAvailability, business hours from SettingsManager, buffers.

Beginner notes:
- This module queries the Booking table to detect conflicts.
- The overlap logic is simple and good enough for a student project demo.
"""

from datetime import timedelta
from django.db.models import Q
from ..models import Booking, Staff


class AvailabilityEngine:
    """
    Provides methods to:
    - Check if a given staff member is free for a specific start time.
    - Build a list of available slots for a day by checking all staff.
    """

    def is_slot_available_for_staff(self, staff: Staff, service, start_time) -> bool:
        """
        Check if 'staff' is free for the duration of 'service' starting at 'start_time'.

        Overlap rule (basic, easy to understand):
        - Compute service duration 'D'.
        - Consider the window [start_time - D, start_time + D).
        - If any existing booking for this staff starts inside that window,
          treat the new slot as conflicting.

        Args:
            staff: Staff instance to check.
            service: Service instance (we need service.duration_minutes).
            start_time: Aware datetime for the candidate start.

        Returns:
            True if no conflict; False if conflict exists.
        """
        duration = timedelta(minutes=service.duration_minutes)
        end_time = start_time + duration

        conflict_exists = Booking.objects.filter(staff=staff).filter(
            Q(start_time__lt=end_time) & Q(start_time__gte=start_time - duration)
        ).exists()

        return not conflict_exists

    def find_available_slots(self, service, date_start, staff_queryset):
        """
        Given a service and a day start, compute all slot starts (business hours),
        then include slots where at least one staff member is free.

        Args:
            service: Service instance (uses service.duration_minutes).
            date_start: Aware datetime marking the start of the target day.
            staff_queryset: QuerySet[Staff] to consider for availability.

        Returns:
            dict with shape:
            {
              "slots": [
                { "start_time": ISO8601_string, "staff_ids": [1,2,...] },
                ...
              ]
            }

        Notes:
            - We delegate slot generation to slot_utils.generate_slots_for_day.
            - We do not filter by staff skills here; you can add that later.
        """
        from .slot_utils import generate_slots_for_day

        # Build candidate slot starts across business hours
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
                results.append(
                    {"start_time": start.isoformat(), "staff_ids": free_staff_ids}
                )

        return {"slots": results}