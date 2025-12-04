# booking/urls.py
#
# Purpose:
# - Expose REST API endpoints for the booking app via DRF router
# - Serve HTML demo/utility pages (login, staff dashboard, booking demo, confirm)
# - Add a public "Cancel Booking" flow:
#     * GET  /api/bookings/cancel/         (renders cancel page)
#     * POST /api/bookings/cancel/submit/  (validates and cancels a booking)
#
# Notes for developers:
# - The REST API routes are registered using DefaultRouter.
# - HTML pages are class-based views wired below.
# - The cancel booking page is implemented in booking/views_cancel.py and
#   its template is at booking/templates/booking/cancel_booking.html.
# - Cancellation POST uses BookingManager to enforce business rules
#   (e.g., 2-hour cutoff) and then sets status="CANCELLED", which triggers
#   notifications/signals to send emails and record Notification entries.

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# API/HTML views you already have
from .auth_views import ClientSignupView, ClientLoginView, ClientLogoutView
from .views_ui import BookingDemoView
from .views_staff_pages import StaffDashboardView
from .views_auth_pages import ClientLoginPage
from .views_confirm_page import BookingConfirmPage

# REST API viewsets (registered on router)
from .views import (
    ClientProfileViewSet,
    ServiceViewSet,
    StaffViewSet,
    BookingViewSet,
    FeedbackViewSet,
)

# New: public cancel booking page + POST action
# (Make sure you created booking/views_cancel.py as shown previously)
from . import views_cancel

# --------------------------
# DRF Router registrations
# --------------------------
router = DefaultRouter()
router.register(r"clients", ClientProfileViewSet, basename="client")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"staff", StaffViewSet, basename="staff")
router.register(r"bookings", BookingViewSet, basename="booking")
router.register(r"feedback", FeedbackViewSet, basename="feedback")  # optional, if you expose feedback

# --------------------------
# URL patterns
# --------------------------
urlpatterns = [
    # 1) REST API (JSON) — all the viewsets above
    path("", include(router.urls)),

    # 2) Auth API (JSON) — existing endpoints for client signup/login/logout
    path("auth/signup", ClientSignupView.as_view()),
    path("auth/login", ClientLoginView.as_view()),
    path("auth/logout", ClientLogoutView.as_view()),

    # 3) HTML Pages
    # Client login page (HTML)
    path("login", ClientLoginPage.as_view()),

    # Staff dashboard (HTML) — you can protect this with @staff_member_required inside the view
    path("staff/dashboard", StaffDashboardView.as_view()),

    # Booking confirmation page (HTML) — expects query string: ?id=&service=&price=&start=&phone=
    path("confirm", BookingConfirmPage.as_view()),

    # Demo booking page (HTML) — your public booking UI
    path("demo/booking", BookingDemoView.as_view()),

    # 4) Public Cancel Booking flow (HTML + POST)
    # GET  /api/bookings/cancel/         -> renders the cancel page (HTML)
    path("bookings/cancel/", views_cancel.cancel_booking_page, name="cancel_booking_page"),
    # POST /api/bookings/cancel/submit/  -> accepts form post, validates, applies business rules, cancels
    path("bookings/cancel/submit/", views_cancel.cancel_booking_action, name="cancel_booking_action"),
]