# notifications/signals.py
#
# Purpose:
# - Send emails when Booking status changes.
#   * CONFIRMED: on create, or when status changes to CONFIRMED
#   * CANCELLED: on update when status is set to CANCELLED
#
# Notes:
# - Uses DEFAULT_FROM_EMAIL from settings.
# - Works with either console backend (dev) or SMTP (demo/prod).
# - Does not crash the request on email failures (logs instead).
#
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from booking.models import Booking
from notifications.models import Notification


def _send(subject: str, body: str, to_email: str):
    """
    Helper to send a single email.

    In dev (console backend), this prints to terminal.
    In demo/prod (SMTP backend with env vars or hardcoded settings), this sends a real email.

    We never let an exception bubble up and break the request.
    """
    if not to_email:
        return
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to_email],
            fail_silently=False,  # raise so we can log; we still catch it below
        )
    except Exception as e:
        print(f"[email] send error to {to_email}: {e}")


@receiver(post_save, sender=Booking)
def booking_status_emails(sender, instance: Booking, created: bool, update_fields=None, **kwargs):
    """
    Send emails and create Notification records when Booking status changes.

    Logic:
    - CONFIRMED
      * On create: always send
      * On update: send if update_fields is None (unknown) or includes 'status'
    - CANCELLED
      * Only send on update (not on create), to avoid spamming in default= state
    """
    status_val = getattr(instance, "status", None)

    # =========================
    # 1) Booking CONFIRMED flow
    # =========================
    if status_val == "CONFIRMED":
        should_send = False
        if created:
            should_send = True
        else:
            # If we saved with update_fields, only send if 'status' changed
            uf = kwargs.get("update_fields", update_fields)
            if uf is None or "status" in uf:
                should_send = True

        if should_send:
            client = instance.client
            dt_str = instance.start_time.strftime("%A, %B %d, %Y at %I:%M %p")
            body = (
                f"Hi {client.name},\n\n"
                f"Your booking is confirmed.\n\n"
                f"Booking ID: {instance.id}\n"
                f"Service: {instance.service.name}\n"
                f"Date & Time: {dt_str}\n\n"
                f"We look forward to seeing you!\n"
                f"— Hair by Lasheka"
            )

            # Record the message in our Notification table for auditing
            Notification.objects.create(user=client, message=body, sent=True)

            # Send the email to the client
            _send("Booking Confirmation", body, client.email)

    # =========================
    # 2) Booking CANCELLED flow
    # =========================
    if status_val == "CANCELLED" and not created:
        client = instance.client
        dt_str = instance.start_time.strftime("%A, %B %d, %Y at %I:%M %p")
        now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

        body_client = (
            f"Dear {client.name},\n\n"
            f"Your appointment for {instance.service.name} on {dt_str} has been cancelled.\n"
            f"If this was unexpected, please reply to this email.\n"
        )

        # Record notification and send client email
        Notification.objects.create(user=client, message=body_client, sent=True)
        _send(f"Booking #{instance.id} Cancelled", body_client, client.email)

        # Optional owner/admin alert: only if EMAIL_HOST_USER is configured
        owner_email = getattr(settings, "EMAIL_HOST_USER", None)
        if owner_email:
            body_owner = (
                f"ALERT: Booking #{instance.id} cancelled.\n"
                f"Client: {client.name} ({client.email})\n"
                f"Service: {instance.service.name}\n"
                f"Original Time: {dt_str}\n"
                f"Cancellation Time: {now_str}\n"
            )
            _send(f"ALERT: Booking #{instance.id} CANCELLED", body_owner, owner_email)