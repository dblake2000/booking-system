from django.db import models
from django.core.validators import MinValueValidator

# --- CLIENT MODEL ---
class ClientProfile(models.Model):
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
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]  # duration must be >= 1
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]  # price must be > 0
    )

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

    Optional enhancement:
    - status: 'CONFIRMED' or 'CANCELLED' so we don't delete rows when cancelling.
    """
    STATUS_CHOICES = [
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
    ]

    client = models.ForeignKey('ClientProfile', on_delete=models.CASCADE)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    staff = models.ForeignKey('Staff', on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="CONFIRMED",  # new bookings are confirmed by default
    )

    def __str__(self):
        return f"{self.client.name} → {self.service.name} on {self.start_time.strftime('%Y-%m-%d %H:%M')}"