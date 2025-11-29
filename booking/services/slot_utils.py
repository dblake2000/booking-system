"""
slot_utils.py
-------------
Helpers to convert a date string into a timezone-aware day window and to generate
candidate appointment slots within business hours.

Alignment with SRS/SDS:
- SRS 7.0 Date & Time Selection: Show available dates/times and prevent past times.
- SDS AvailabilityEngine: Supplies raw slot times for conflict/availability checks.

Notes for beginners:
- This file does NOT talk to the database except to read two simple settings
  (BUSINESS_OPEN / BUSINESS_CLOSE) if they exist.
- Returned times are timezone-aware (they include time zone info).
"""

from datetime import datetime, timedelta, time
from django.utils import timezone


# ------------------------------------------------------------
# Internal helpers for business hours (configurable via DB)
# ------------------------------------------------------------

def _parse_hhmm(value: str) -> time:
    """
    Parse 'HH:MM' strings (e.g., '09:00') into a time object.
    If parsing fails, raise ValueError so we can handle upstream.
    """
    h, m = value.split(":")
    return time(int(h), int(m))


def get_business_hours():
    """
    Return (open_time, close_time) as time objects.

    Priority:
    1) If SystemSetting has BUSINESS_OPEN/BUSINESS_CLOSE, use those.
    2) Otherwise, default to 09:00–17:00.

    We keep this very simple so beginners can follow.
    """
    default_open = time(9, 0)
    default_close = time(17, 0)

    try:
        # Import here so this module can still be used even if configmgr is missing
        from configmgr.models import SystemSetting

        open_row = SystemSetting.objects.filter(key="BUSINESS_OPEN").first()
        close_row = SystemSetting.objects.filter(key="BUSINESS_CLOSE").first()

        if open_row and close_row:
            try:
                return _parse_hhmm(open_row.value), _parse_hhmm(close_row.value)
            except Exception:
                # If stored values are bad, fall back to defaults
                return default_open, default_close

        # If one or both are missing, fall back to defaults
        return default_open, default_close

    except Exception:
        # If configmgr app or table isn't ready yet, use defaults
        return default_open, default_close


# ------------------------------------------------------------
# Public functions used by the Availability endpoint
# ------------------------------------------------------------

def date_to_range(date_str: str):
    """
    Convert a date string 'YYYY-MM-DD' into a timezone-aware day window.

    Args:
        date_str: e.g., '2025-12-01'

    Returns:
        (day_start, day_end) as timezone-aware datetimes in the project's current timezone.

    Raises:
        ValueError: if the format is invalid (e.g., not 'YYYY-MM-DD').
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
    open_time: time | None = None,
    close_time: time | None = None,
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
        open_time: Business opening time (if None, will read from SystemSetting).
        close_time: Business closing time (if None, will read from SystemSetting).
        date_start: A timezone-aware datetime marking the start of the day
                    (use date_to_range(...)[0]).

    Returns:
        List[datetime]: aware datetimes for each slot's start time.

    Example:
        slots = generate_slots_for_day(60, date_start=tz_aware_midnight)
        -> [09:00, 10:00, 11:00, ... up to closing - duration]
    """
    assert date_start is not None, "date_start must be provided (use date_to_range(...)[0])"

    # If no hours provided, read from settings (falls back to 09:00–17:00)
    if open_time is None or close_time is None:
        open_time, close_time = get_business_hours()

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