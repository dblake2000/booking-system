# booking/models.py
#
# Purpose:
# - Core domain models for the booking system.
#
# Design highlights:
# - ClientProfile: Optional link to auth User (public can book without login).
#   • clean() prevents duplicates by (name/email case-insensitive + phone exact).
# - Service: Validates price and duration; "active" flag controls visibility.
# - Staff: Basic identity for stylists; unique email for admin clarity.
# - Booking:
#   • Records client, service, staff (optional), start_time
#   • status is uppercase "CONFIRMED" or "CANCELLED"
#   • cancellation_time records when a cancellation occurs
# - Feedback: One-to-one with Booking after the appointment.
# - PriceHistory: Records service price changes.
#
# Notes for developers:
# - Duplicate ClientProfile prevention:
#   We handle it in model.clean() so admin and any entry points respect it.
#   The API's "create client" endpoint should also “find-or-create” before adding.
# - If you want DB-level uniqueness later (PostgreSQL), add a migration with a
#   UniqueConstraint on Lower(name), Lower(email), and phone. This is not included
#   here to keep it portable (SQLite doesn’t support function-based unique nicely).
#

from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


# -------------------------
# Client (person who books)
# -------------------------
class ClientProfile(models.Model):
    """
    A client who books an appointment.
    - 'user' link is optional (public can book with just name/email/phone).
    - We prevent duplicates by using a case-insensitive match on name and email,
      and exact match on phone in model.clean().
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="client_profile",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    def clean(self):
        """
        Soft duplicate prevention (app-level):
        - Disallow another profile with same (name/email case-insensitive) + phone exact.
        - Allows saving when updating the same record (excludes self.pk).
        - This runs in admin and forms/serializers that call full_clean().
        """
        # Normalize for comparison
        name = (self.name or "").strip()
        email = (self.email or "").strip()
        phone = (self.phone or "").strip()

        # If any key fields are missing, let the form/serializer handle "required".
        if not name or not email or not phone:
            return

        qs = ClientProfile.objects.filter(
            name__iexact=name,
            email__iexact=email,
            phone=phone,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError(
                "A client with the same name, email, and phone already exists."
            )

    # If you later want DB-level uniqueness (recommended for Postgres):
    # 1) Create a migration with UniqueConstraint using Lower(name), Lower(email), phone.
    # 2) Keep this clean() for admin UX and helpful errors.
    #
    # Example (Postgres only, not included here):
    # from django.db.models.functions import Lower
    # class Migration(migrations.Migration):
    #     operations = [
    #         migrations.AddConstraint(
    #             model_name="clientprofile",
    #             constraint=models.UniqueConstraint(
    #                 Lower("name"), Lower("email"), "phone",
    #                 name="uniq_clientprofile_name_email_phone_ci",
    #             ),
    #         ),
    #     ]


# -------------------------
# Service catalog item
# -------------------------
class Service(models.Model):
    """
    A service offered by the salon.

    Rules:
    - price must be > 0
    - duration_minutes must be > 0
    - active controls visibility and bookability
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


# -------------------------
# Staff member / Stylist
# -------------------------
class Staff(models.Model):
    """
    A stylist or staff member who can be assigned to bookings.
    """
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# -------------------------
# Booking record
# -------------------------
class Booking(models.Model):
    """
    Appointment booking.

    Enhancement:
    - status keeps history (CONFIRMED/CANCELLED)
    - optional cancellation_time records when a booking was cancelled
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
        help_text="Booking lifecycle status",
    )
    cancellation_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the booking was cancelled (if applicable).",
    )

    def __str__(self):
        return f"{self.client.name} → {self.service.name} on {self.start_time}"


# -------------------------
# Service price change log
# -------------------------
class PriceHistory(models.Model):
    """
    Record of changes to service price, for auditing/reporting.
    """
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="price_changes")
    old_price = models.DecimalField(max_digits=8, decimal_places=2)
    new_price = models.DecimalField(max_digits=8, decimal_places=2)
    changed_at = models.DateTimeField(auto_now_add=True)


# -------------------------
# Post-appointment feedback
# -------------------------
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