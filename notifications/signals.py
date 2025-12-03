# notifications/signals.py
#
# Purpose:
# - Listen for changes on Booking and, when status becomes "confirmed",
#   send a confirmation email and create a Notification record.
#
# How it’s loaded:
# - apps.py (NotificationsConfig.ready) imports this module so the receiver
#   is registered when Django starts.
#
# Safety:
# - Exits early if email is missing or status is not "confirmed".
# - Formats date/time readably; falls back gracefully if formatting fails.
#
# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from booking.models import Booking  # sender
from notifications.models import Notification  # target row to create


@receiver(post_save, sender=Booking)
def send_booking_confirmation_email(sender, instance, created, **kwargs):
    """
    When a Booking is saved with status='confirmed', send an email and
    record a Notification. Safe to call on both create and update.
    """
    if getattr(instance, "status", None) != "confirmed":
        return

    client_profile = getattr(instance, "client", None)
    if client_profile is None:
        return

    client_name = getattr(client_profile, "name", "") or "Valued Client"
    client_email = getattr(client_profile, "email", None)
    if not client_email:
        return

    booking_id = getattr(instance, "id", None)
    service_name = getattr(getattr(instance, "service", None), "name", "your appointment")

    try:
        dt_str = instance.start_time.strftime("%A, %B %d, %Y at %I:%M %p")
    except Exception:
        dt_str = str(instance.start_time)

    subject = f"Booking Confirmation — {service_name}"
    message = (
        f"Hi {client_name},\n\n"
        f"This is your booking confirmation.\n\n"
        f"Booking ID: {booking_id}\n"
        f"Service: {service_name}\n"
        f"Date & Time: {dt_str}\n\n"
        f"We can’t wait to see you! If you need to make changes, simply reply to this email.\n\n"
        f"— Hair by Lasheka"
    )

    # Create Notification record
    Notification.objects.create(user=client_profile, message=message, sent=True)

    # Send email
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[client_email],
        fail_silently=False,
    )