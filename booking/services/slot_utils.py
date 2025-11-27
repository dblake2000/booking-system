"""
slot_utils.py
-------------
Helpers to convert a date string into a timezone-aware day window and to generate
candidate appointment slots within business hours.

Alignment with SRS/SDS:
- SRS 7.0 Date & Time Selection: We need to show available dates/times and prevent
  past times from being selectable.
- SDS AvailabilityEngine: This module supplies the raw slot times that the engine
  will evaluate for conflicts and staff availability.

Notes for beginners:
- These utilities do not touch the database.
- They only calculate time ranges and slot start times for a single day.
"""

from datetime import datetime, timedelta, time
from django.utils import timezone


def date_to_range(date_str: str):
    """
    Convert a date string 'YYYY-MM-DD' into a timezone-aware day window.

    Args:
        date_str: e.g., '2025-12-01'

    Returns:
        (day_start, day_end) as timezone-aware datetimes in the project's current timezone.

    Raises:
        ValueError: if the format is invalid (e.g., not YYYY-MM-DD).
    """
    # Split string and convert to integers (year, month, day)
    y, m, d = map(int, date_str.split("-"))

    # Get the current Django timezone (set in settings.py or defaults to local)
    tz = timezone.get_current_timezone()

    # Build a naive datetime at midnight, then "localize" it to make it timezone-aware
    day_start = tz.localize(datetime(y, m, d, 0, 0, 0))

    # Day end is simply 24 hours after day start
    day_end = day_start + timedelta(days=1)

    return day_start, day_end


def generate_slots_for_day(
    service_duration_minutes: int,
    open_time: time = time(9, 0),
    close_time: time = time(17, 0),
    date_start=None,
):
    """
    Generate candidate slot start times between open and close hours.

    Approach:
    - The step size equals the selected service's duration (e.g., 60 minutes).
    - We keep adding duration until we reach closing time.
    - Returned datetimes are timezone-aware.

    Args:
        service_duration_minutes: Appointment length in minutes.
        open_time: Business opening time (default 09:00).
        close_time: Business closing time (default 17:00).
        date_start: A timezone-aware datetime marking the start of the day
                    (use date_to_range(...)[0]).

    Returns:
        List[datetime]: aware datetimes for each slot's start time.

    Example:
        slots = generate_slots_for_day(60, date_start=tz_aware_midnight)
        -> [09:00, 10:00, 11:00, ... up to 16:00]
    """
    assert date_start is not None, "date_start must be provided (use date_to_range(...)[0])"

    tz = date_start.tzinfo
    slot = timedelta(minutes=service_duration_minutes)

    # Build the day's opening and closing datetimes (aware)
    day_open = tz.localize(
        datetime(
            date_start.year,
            date_start.month,
            date_start.day,
            open_time.hour,
            open_time.minute,
        )
    )
    day_close = tz.localize(
        datetime(
            date_start.year,
            date_start.month,
            date_start.day,
            close_time.hour,
            close_time.minute,
        )
    )

    # Generate candidate starts stepping by the appointment duration
    slots = []
    current = day_open
    while current + slot <= day_close:
        slots.append(current)
        current += slot

    return slots