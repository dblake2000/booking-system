"""
NotificationService
-------------------
Purpose (SRS 6.0 / SRS 4.0 / SDS Notification Server):
- Send booking-related notifications.
- In development, we use Django's console email backend to keep it 100% free.
- In production, switch EMAIL_BACKEND to SMTP to send real emails.

How it aligns:
- SRS 6.0 Booking Confirmation: send confirmation immediately after booking.
- SRS 3.0 Cancellation: send a cancellation notice when a booking is cancelled.
- SRS 4.0 Reminders: send reminders at 48h/24h before appointment (management command).
- SRS 10.0 Feedback (optional): send "please leave feedback" after appointment time.

Notes for beginners:
- With EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend",
  emails are printed to your runserver terminal (free).
"""

from django.core.mail import send_mail
from django.conf import settings


class NotificationService:
    """
    Sends confirmation, cancellation, reminder, and (optional) feedback request emails.

    Dev mode:
    - With EMAIL_BACKEND = console.EmailBackend, 'send_mail' prints messages in the terminal.

    Future:
    - Switch to SMTP by changing EMAIL_BACKEND and adding credentials in settings.py.
    """

    def send_confirmation(self, booking) -> None:
        """
        Send a booking confirmation "email" to the client (console print in dev).

        Args:
            booking: Booking model instance just created.
        """
        subject = f"Booking Confirmation #{booking.id}"
        # Plain text body for demo simplicity
        body = (
            f"Hi {booking.client.name},\n\n"
            f"Your appointment is confirmed.\n"
            f"- Service: {booking.service.name}\n"
            f"- Price: ${booking.service.price}\n"
            f"- Date/Time: {booking.start_time}\n"
            f"- Staff: {booking.staff.name if booking.staff else 'TBA'}\n\n"
            "Thank you for booking with Hair by Lasheka!"
        )
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.client.email],
            fail_silently=False,  # Show errors in console to help beginners debug
        )

    def send_cancellation(self, booking_snapshot: dict) -> None:
        """
        Send a booking cancellation notification to the client (console print in dev).

        Args:
            booking_snapshot: dict captured before delete OR built from instance, with keys:
              - id (booking id)
              - client_email
              - start_time
        """
        subject = f"Booking Cancellation #{booking_snapshot.get('id')}"
        body = (
            "Hello,\n\nYour appointment was cancelled.\n"
            f"- Date/Time: {booking_snapshot.get('start_time')}\n"
            "We hope to see you again soon."
        )
        recipient = booking_snapshot.get("client_email")
        if recipient:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
    # -------------------------------
    # New helpers (Reminders + Feedback)
    # -------------------------------

    def send_reminder(self, booking, hours_before: int) -> None:
        """
        Send a reminder "email" to the client (console print in dev).

        Args:
            booking: Booking model instance.
            hours_before: 48 or 24 (SRS 4.0 reminder windows).
        """
        subject = f"Appointment Reminder ({hours_before}h) — Booking #{booking.id}"
        body = (
            f"Hi {booking.client.name},\n\n"
            "This is a reminder for your upcoming appointment.\n"
            f"- Service: {booking.service.name}\n"
            f"- Date/Time: {booking.start_time}\n"
            f"- Staff: {booking.staff.name if booking.staff else 'TBA'}\n\n"
            "See you soon!"
        )
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.client.email],
            fail_silently=False,
        )

    def send_feedback_request(self, booking) -> None:
        """
        Send a 'please leave feedback' message (console print in dev).

        Args:
            booking: Booking model instance (typically after appointment time passes).
        """
        subject = f"Please leave feedback — Booking #{booking.id}"
        body = (
            f"Hi {booking.client.name},\n\n"
            "We hope your appointment went well!\n"
            "Please leave a quick rating and comment.\n\n"
            "(This is a demo message printed to the terminal.)"
        )
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.client.email],
            fail_silently=False,
        )