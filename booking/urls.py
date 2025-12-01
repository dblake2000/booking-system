from django.urls import include, path
from .auth_views import ClientSignupView, ClientLoginView, ClientLogoutView
from .views_ui import BookingDemoView
from rest_framework.routers import DefaultRouter
from .views_staff_pages import StaffDashboardView
from .views_auth_pages import ClientLoginPage
from .views_confirm_page import BookingConfirmPage
from .views import (
    ClientProfileViewSet,
    ServiceViewSet,
    StaffViewSet,
    BookingViewSet,
    FeedbackViewSet
)

router = DefaultRouter()
router.register(r"clients", ClientProfileViewSet, basename="client")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"staff", StaffViewSet, basename="staff")
router.register(r"bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("", include(router.urls)),

    # Auth API (JSON)
    path("auth/signup", ClientSignupView.as_view()),
    path("auth/login", ClientLoginView.as_view()),
    path("auth/logout", ClientLogoutView.as_view()),

    # HTML pages
    path("login", ClientLoginPage.as_view()),           # /api/login (client login page)
    path("staff/dashboard", StaffDashboardView.as_view()),  # staff-only page
    path("confirm", BookingConfirmPage.as_view()),      # /api/confirm?id=..&service=..&price=..&start=..
    path("demo/booking", BookingDemoView.as_view()),    # /api/demo/booking (demo booking page)
]