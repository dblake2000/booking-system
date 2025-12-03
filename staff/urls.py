from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaffAvailabilityViewSet

router = DefaultRouter()
router.register(r"availability", StaffAvailabilityViewSet, basename="staff-availability")

urlpatterns = [path("", include(router.urls))]