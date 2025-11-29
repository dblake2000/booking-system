from django.contrib import admin
from .models import ClientProfile, Service, Staff, Booking, PriceHistory

admin.site.register(ClientProfile)
admin.site.register(Service)
admin.site.register(Staff)
admin.site.register(Booking)

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("service", "old_price", "new_price", "changed_at")
    list_filter = ("service",)