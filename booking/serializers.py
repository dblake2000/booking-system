from rest_framework import serializers
from .models import ClientProfile, Service, Staff, Booking, Feedback
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
    


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["id", "booking", "rating", "comment", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        # Ensure only allow feedback after appointment time has passed
        booking = attrs.get("booking")
        if booking and booking.start_time >= timezone.now():
            raise serializers.ValidationError("Feedback can be submitted only after the appointment time.")
        # Optional: ensure rating 1..5
        rating = attrs.get("rating")
        if rating is not None and (rating < 1 or rating > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        # Optional: if a status field exists, block if cancelled
        if hasattr(booking, "status") and booking.status == "CANCELLED":
            raise serializers.ValidationError("Cannot submit feedback for a cancelled appointment.")
        return attrs
    