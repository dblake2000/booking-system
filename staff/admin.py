# staff/admin.py
from django.contrib import admin
from .models import StaffAvailability  # Only availability is managed here

@admin.register(StaffAvailability)
class StaffAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("staff", "start_time", "end_time")
    list_filter = ("staff",)
    search_fields = ("staff__name",)