from rest_framework import viewsets
from rest_framework.permissions import BasePermission
from .models import StaffAvailability
from .serializers import StaffAvailabilitySerializer

class IsStaffOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

class StaffAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = StaffAvailability.objects.all().order_by("staff_id", "start_time")
    serializer_class = StaffAvailabilitySerializer
    permission_classes = [IsStaffOnly]