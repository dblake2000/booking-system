# booking/views_calendar.py
#
# Purpose:
# - Staff‑only month-view calendar of bookings at /admin/bookings-calendar/.
# - Renders a simple, server-side month grid with bookings per day.
#
# Template:
# - booking/templates/booking_calendar.html
#   (If you keep templates directly under booking/templates/, use "booking_calendar.html" as name)
#
# Behavior:
# - Only staff (or superusers) can access (enforced by @staff_member_required).
# - Query params: ?year=YYYY&month=MM (defaults to current month if missing/invalid).
# - Excludes bookings with status = "CANCELLED" so the calendar reflects availability.
#
from datetime import datetime
import calendar

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone

from .models import Booking


@staff_member_required
def bookings_calendar(request):
    """
    Render a staff-only month calendar.

    Query parameters:
      - year (int): YYYY (defaults to current year)
      - month (int): 1..12 (defaults to current month)

    Implementation details:
      - We use timezone-aware datetimes for day bounds, based on the current timezone.
      - We exclude bookings with status == "CANCELLED" so the calendar only shows active/confirmed entries.
      - We build a flat 'cells' list with leading blanks for the first week so the template can render a grid.
    """
    # Determine the active timezone (as configured in settings TIME_ZONE)
    tz = timezone.get_current_timezone()
    today = timezone.localtime(timezone.now(), tz)

    # 1) Parse year/month safely with fallbacks
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not (1 <= month <= 12):
            raise ValueError()
    except Exception:
        year, month = today.year, today.month

    # 2) Calculate timezone-aware month bounds:
    #    start_dt = first day at 00:00:00
    #    end_dt   = last day at 23:59:59 (to include bookings on the last day)
    _, last_day_num = calendar.monthrange(year, month)
    start_dt = timezone.make_aware(datetime(year, month, 1, 0, 0, 0), tz)
    end_dt = timezone.make_aware(datetime(year, month, last_day_num, 23, 59, 59), tz)

    # 3) Query month’s bookings, EXCLUDING cancelled ones.
    #    We also fetch related client/service/staff for display without N+1 queries.
    qs = (
        Booking.objects
        .filter(start_time__gte=start_dt, start_time__lte=end_dt)
        .exclude(status="CANCELLED")  # Do not show cancelled bookings in the calendar
        .select_related("client", "service", "staff")
        .order_by("start_time")
    )

    # 4) Build a map: day number -> list of bookings with display fields
    #    We convert each booking’s start_time to the current tz for correct day assignment.
    days_map = {d: [] for d in range(1, last_day_num + 1)}
    for b in qs:
        local_start = timezone.localtime(b.start_time, tz)
        # Prepare readable fields for template:
        entry = {
            "time": local_start.strftime("%I:%M %p"),
            "client": getattr(b.client, "name", "Client"),
            "service": getattr(b.service, "name", "Service"),
            "staff": getattr(getattr(b, "staff", None), "name", None),
            "status": getattr(b, "status", ""),  # keep for a tiny badge if needed
            "id": b.id,  # useful for linking to admin change view or details
        }
        days_map[local_start.day].append(entry)

    # 5) Build 'cells' to simplify template rendering:
    #    calendar.monthrange(year, month)[0] gives the first weekday (0=Mon..6=Sun).
    #    We create that many leading blanks and then a cell for each day.
    first_weekday = calendar.monthrange(year, month)[0]  # 0=Mon, 6=Sun
    cells = [{"blank": True} for _ in range(first_weekday)]
    for d in range(1, last_day_num + 1):
        cells.append({
            "blank": False,
            "day": d,
            "bookings": days_map[d],  # list (possibly empty)
        })

    # 6) Calculate previous/next month for navigation links
    #    We adjust year boundaries (Dec -> Jan next year, Jan -> Dec previous year).
    prev_y, prev_m = year, month - 1
    next_y, next_m = year, month + 1
    if prev_m == 0:
        prev_m = 12
        prev_y -= 1
    if next_m == 13:
        next_m = 1
        next_y += 1

    # 7) Context to render
    ctx = {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "cells": cells,                   # flat list used by the template to render the grid
        "prev_year": prev_y, "prev_month": prev_m,
        "next_year": next_y, "next_month": next_m,
    }

    # 8) Render using the app-root template:
    #    If your file is booking/templates/booking_calendar.html, this is the correct template name.
    #    (No subfolder path in the template name)
    return render(request, "booking_calendar.html", ctx)