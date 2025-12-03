"""
slot_utils.py
-------------
Helpers to convert a date string into a timezone-aware day window and to generate
candidate appointment slots within business hours.
"""

from datetime import datetime, timedelta, time
from django.utils import timezone


def _parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def get_business_hours():
    """
    Return (open_time, close_time) as time objects.
    Defaults to 09:00–17:00 if none are configured.
    """
    default_open = time(9, 0)
    default_close = time(17, 0)

    try:
        from configmgr.models import SystemSetting

        open_row = SystemSetting.objects.filter(key="BUSINESS_OPEN").first()
        close_row = SystemSetting.objects.filter(key="BUSINESS_CLOSE").first()

        if open_row and close_row:
            try:
                return _parse_hhmm(open_row.value), _parse_hhmm(close_row.value)
            except Exception:
                return default_open, default_close
        return default_open, default_close
    except Exception:
        return default_open, default_close


def _make_aware(dt_naive: datetime):
    """
    Convert a naive datetime to an aware one using Django's current timezone.
    This works with zoneinfo-based timezones (Django 4+).
    """
    if timezone.is_aware(dt_naive):
        return dt_naive
    return timezone.make_aware(dt_naive, timezone.get_current_timezone())


def date_to_range(date_str: str):
    """
    Convert 'YYYY-MM-DD' into a timezone-aware day window [start, end).
    """
    date_str = (date_str or "").strip()
    y, m, d = map(int, date_str.split("-"))

    # Build naive midnight, then make aware with Django's TZ
    day_start_naive = datetime(y, m, d, 0, 0, 0)
    day_start = _make_aware(day_start_naive)
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
    Returned datetimes are timezone-aware.
    """
    assert date_start is not None, "date_start must be provided (use date_to_range(...)[0])"

    if open_time is None or close_time is None:
        open_time, close_time = get_business_hours()

    slot = timedelta(minutes=service_duration_minutes)

    # Build naive open/close for the given day, then make aware
    day_open_naive = datetime(
        date_start.year, date_start.month, date_start.day,
        open_time.hour, open_time.minute, 0
    )
    day_close_naive = datetime(
        date_start.year, date_start.month, date_start.day,
        close_time.hour, close_time.minute, 0
    )
    day_open = _make_aware(day_open_naive)
    day_close = _make_aware(day_close_naive)

    # Generate candidate starts stepping by the service duration
    slots = []
    current = day_open
    while current + slot <= day_close:
        slots.append(current)
        current += slot

    return slots