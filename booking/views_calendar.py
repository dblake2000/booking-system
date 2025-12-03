# booking/views_calendar.py
#
# Purpose:
# - Staff-only month-view calendar of bookings at /admin/bookings-calendar/.
# Templates:
# - Uses booking/templates/booking_calendar.html (template at app root templates dir)
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
    Staff-only calendar showing bookings for the selected month.
    Query params:
      - year: YYYY (defaults to current)
      - month: 1..12 (defaults to current)
    """
    tz = timezone.get_current_timezone()
    today = timezone.localtime(timezone.now(), tz)

    # Parse year/month safely
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not (1 <= month <= 12):
            raise ValueError()
    except Exception:
        year, month = today.year, today.month

    # Month bounds
    _, last_day_num = calendar.monthrange(year, month)
    start_dt = timezone.make_aware(datetime(year, month, 1, 0, 0, 0), tz)
    end_dt = timezone.make_aware(datetime(year, month, last_day_num, 23, 59, 59), tz)

    # Query bookings
    qs = (
        Booking.objects.filter(start_time__gte=start_dt, start_time__lte=end_dt)
        .select_related("client", "service", "staff")
        .order_by("start_time")
    )

    # Build days -> bookings map
    days_map = {d: [] for d in range(1, last_day_num + 1)}
    for b in qs:
        local_start = timezone.localtime(b.start_time, tz)
        days_map[local_start.day].append(
            {
                "time": local_start.strftime("%I:%M %p"),
                "client": getattr(b.client, "name", "Client"),
                "service": getattr(b.service, "name", "Service"),
                "staff": getattr(getattr(b, "staff", None), "name", None),
                "status": getattr(b, "status", ""),
                "id": b.id,
            }
        )

    # Build grid cells with leading blanks (0=Mon..6=Sun)
    first_weekday = calendar.monthrange(year, month)[0]
    cells = [{"blank": True} for _ in range(first_weekday)]
    for d in range(1, last_day_num + 1):
        cells.append({"blank": False, "day": d, "bookings": days_map[d]})

    # Prev/next month
    prev_y, prev_m = year, month - 1
    next_y, next_m = year, month + 1
    if prev_m == 0:
        prev_m = 12
        prev_y -= 1
    if next_m == 13:
        next_m = 1
        next_y += 1

    ctx = {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "cells": cells,
        "prev_year": prev_y,
        "prev_month": prev_m,
        "next_year": next_y,
        "next_month": next_m,
    }

    # IMPORTANT: your template path is booking/templates/booking_calendar.html
    return render(request, "booking_calendar.html", ctx)