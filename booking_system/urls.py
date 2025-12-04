# booking_system/urls.py
#
# Purpose:
# - Project URL router.
# - Separates public-facing HTML pages (e.g., cancel page) from the JSON API.
# - Keeps DRF router under /api/ to avoid collisions with HTML routes.
#
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Staff master calendar (HTML)
from booking.views_calendar import bookings_calendar

# Public cancellation views (HTML page + POST handler)
from booking import views_cancel


urlpatterns = [
    # ================
    # Staff-only pages
    # ================
    # NOTE: We place the calendar at /admin/bookings-calendar/ by convention.
    path("admin/bookings-calendar/", bookings_calendar, name="bookings_calendar"),

    # Django admin
    path("admin/", admin.site.urls),

    # ==========
    # Public HTML
    # ==========
    # Customer-facing "Cancel Booking" page (non-API path to avoid DRF router conflicts)
    path("bookings/cancel/", views_cancel.cancel_booking_page, name="cancel_booking_page"),
    # The POST endpoint that processes the cancellation form from the page above
    path("bookings/cancel/submit/", views_cancel.cancel_booking_action, name="cancel_booking_action"),

    # =====
    # API's
    # =====
    # All JSON APIs remain under /api/ via DRF router to keep URL space clean.
    path("api/", include("booking.urls")),
    path("api/staff/", include("staff.urls")),
    path("api/reports/", include("reports.urls")),
]

# Static files in DEBUG (dev only). In production, serve via web server / CDN.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)