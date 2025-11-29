from rest_framework import serializers
from .models import ClientProfile, Service, Staff, Booking
from django.utils import timezone

class ClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = ["id", "name", "email"]

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price"]

class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ["id", "name", "email", "role"]

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "client",
            "service",
            "staff",
            "start_time",
            "created_at",
            "notes",
            "status",  # expose status
        ]
        read_only_fields = ["created_at", "status"]  # API cannot set status directly

    def validate(self, attrs):
        # SRS 7.0: prevent past dates
        start_time = attrs.get("start_time")
        if start_time and start_time <= timezone.now():
            raise serializers.ValidationError("Start time must be in the future.")
        return attrs