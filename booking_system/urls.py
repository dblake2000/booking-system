# booking_system/urls.py
#
# Purpose:
# - Project URL router.
# - Exposes Django admin, your API, and a staff-only bookings calendar.
#
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Staff-only calendar — MUST be before "admin/" catch-all behavior
    path("admin/bookings-calendar/", bookings_calendar, name="bookings_calendar"),

    # Django admin
    path("admin/", admin.site.urls),

    # Your API
    path("api/", include("booking.urls")),
    path("api/staff/", include("staff.urls")),
    path("api/reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)