from django.contrib import admin
from .models import Staff, StaffAvailability

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role")

@admin.register(StaffAvailability)
class StaffAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("staff", "start_time", "end_time")
    list_filter = ("staff",)