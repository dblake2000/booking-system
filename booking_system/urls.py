# booking_system/urls.py
#
# Purpose:
# - Project URL router.
# - Exposes Django admin, your API, and a staff-only bookings calendar.
#
from django.contrib import admin
from django.urls import path, include

# IMPORTANT: import the view function directly from the booking app
from booking.views_calendar import bookings_calendar

urlpatterns = [
    # Staff-only calendar — MUST be before "admin/" catch-all behavior
    path("admin/bookings-calendar/", bookings_calendar, name="bookings_calendar"),

    # Django admin
    path("admin/", admin.site.urls),

    # Your API
    path("api/", include("booking.urls")),
]