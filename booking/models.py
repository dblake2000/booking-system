from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User

# --- CLIENT MODEL ---
class ClientProfile(models.Model):
    """
    Extends Django's User for clients.
    Each client user has exactly one ClientProfile.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


# --- SERVICE MODEL ---
class Service(models.Model):
    """
    Service offered by the salon.

    Rules:
    - price must be > 0
    - duration_minutes must be > 0
    - active controls whether it appears in the catalog and can be booked
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]  # duration must be >= 1 minute
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],  # price must be > 0
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (${self.price})"


# --- STAFF MODEL ---
class Staff(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# --- BOOKING MODEL ---
class Booking(models.Model):
    """
    Appointment booking.

    Enhancement:
    - status keeps history (Confirmed/Cancelled)
    """
    STATUS_CHOICES = [
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
    ]

    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="CONFIRMED",
    )

    def __str__(self):
        return f"{self.client.name} → {self.service.name} on {self.start_time}"


# --- FEEDBACK MODEL (optional, SRS 10.0) ---
class Feedback(models.Model):
    """
    Feedback for a completed appointment.
    """
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField()  # 1..5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for booking #{self.booking_id} (rating {self.rating})"
    
class PriceHistory(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="price_changes")
    old_price = models.DecimalField(max_digits=8, decimal_places=2)
    new_price = models.DecimalField(max_digits=8, decimal_places=2)
    changed_at = models.DateTimeField(auto_now_add=True)

class Feedback(models.Model):
    """
    Feedback for a completed appointment.
    """
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField()  # 1..5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for booking #{self.booking_id} (rating {self.rating})"