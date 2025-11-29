from django.urls import include, path
from rest_framework.routers import DefaultRouter
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
router.register(r"feedback", FeedbackViewSet, basename="feedback")

urlpatterns = [
    path("", include(router.urls)),
]