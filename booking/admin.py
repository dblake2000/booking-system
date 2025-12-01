from django.contrib import admin
from .models import Service, ClientProfile, Staff, Booking, PriceHistory, Feedback

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "duration_minutes", "active")
    list_filter = ("active",)
    search_fields = ("name",)
    list_editable = ("price", "duration_minutes", "active")  # allow inline toggle
    # If inline edit gives errors (due to validation), remove list_editable and edit in the form page instead.

@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email")

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role")

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "service", "staff", "start_time", "status")
    list_filter = ("status", "service")
    search_fields = ("client__name", "service__name")

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("service", "old_price", "new_price", "changed_at")
    list_filter = ("service",)
    search_fields = ("service__name",)

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("booking", "rating", "created_at")
    list_filter = ("rating",)