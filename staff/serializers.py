from rest_framework import serializers
from .models import StaffAvailability

class StaffAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffAvailability
        fields = ["id", "staff", "start_time", "end_time"]