from rest_framework import serializers
from django.utils import timezone
from .models import ClientProfile, Service, Staff, Booking, Feedback

class ClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = ["id", "name", "email", "phone"]  # include phone


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price"]


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ["id", "name", "email", "role"]


class BookingSerializer(serializers.ModelSerializer):
    # Explicitly accept PKs (optional; DRF can infer)
    client = serializers.PrimaryKeyRelatedField(queryset=ClientProfile.objects.all())
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    staff = serializers.PrimaryKeyRelatedField(queryset=Staff.objects.all(), allow_null=True, required=False)

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
            "status",
        ]
        read_only_fields = ["created_at", "status"]

    def validate(self, attrs):
        # prevent past dates
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
        booking = attrs.get("booking")
        if booking and booking.start_time >= timezone.now():
            raise serializers.ValidationError("Feedback can be submitted only after the appointment time.")
        rating = attrs.get("rating")
        if rating is not None and (rating < 1 or rating > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        if hasattr(booking, "status") and booking.status == "CANCELLED":
            raise serializers.ValidationError("Cannot submit feedback for a cancelled appointment.")
        return attrs