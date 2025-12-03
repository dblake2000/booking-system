from django.contrib import admin
from .models import ClientProfile, Service, Staff, Booking

admin.site.register(ClientProfile)
admin.site.register(Service)
admin.site.register(Staff)
admin.site.register(Booking)