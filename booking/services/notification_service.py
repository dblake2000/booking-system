"""
NotificationService
-------------------
Purpose (SRS 6.0 / SDS Notification Server):
- Send booking-related notifications.
- In development, we use Django's console email backend to keep it 100% free.
- In production, you can switch EMAIL_BACKEND to SMTP to send real emails.

How it aligns:
- SRS 6.0 Booking Confirmation: send an email (console print) immediately after booking.
- SRS 3.0 Cancellation: send a cancellation notice when a booking is cancelled.
"""

from django.core.mail import send_mail
from django.conf import settings


class NotificationService:
    """
    Sends confirmation and cancellation emails.

    Dev mode:
    - With EMAIL_BACKEND = console.EmailBackend, 'send_mail' prints the message in the terminal.
    - This is free and perfect for demos.

    Future:
    - Switch to SMTP or a free provider by changing EMAIL_BACKEND and adding credentials in settings.
    """

    def send_confirmation(self, booking) -> None:
        """
        Send a booking confirmation "email" to the client.
        For dev/demo, this prints to the runserver terminal.

        Args:
            booking: Booking model instance just created.

        Output:
            Printed email content in the terminal (free).
        """
        subject = f"Booking Confirmation #{booking.id}"
        # NOTE: For demo simplicity we use plain text.
        # You can switch to HTML templates later.
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
        Send a booking cancellation notification to the client.

        Args:
            booking_snapshot: A simple dict captured before deletion with keys:
                - id (booking id)
                - client_email
                - start_time

        Output:
            Printed email content in the terminal (free).
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