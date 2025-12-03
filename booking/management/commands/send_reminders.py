"""
send_reminders.py
-----------------
Django management command to send 48h/24h reminders.

Usage:
    python manage.py send_reminders --when 48
    python manage.py send_reminders --when 24

Behavior:
- Finds bookings whose start_time is about N hours from now (±1 minute window).
- Skips cancelled bookings (requires Booking.status if present).
- Prints reminder "emails" to the terminal via NotificationService (console backend).
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import Booking
from booking.services.notification_service import NotificationService


class Command(BaseCommand):
    help = "Send appointment reminders at N hours (48 or 24) before start_time."

    def add_arguments(self, parser):
        parser.add_argument(
            "--when",
            type=int,
            choices=[48, 24],
            required=True,
            help="Reminder window in hours (choose 48 or 24).",
        )

    def handle(self, *args, **options):
        hours = options["when"]
        now = timezone.now()
        window_start = now + timedelta(hours=hours) - timedelta(minutes=1)
        window_end = now + timedelta(hours=hours) + timedelta(minutes=1)

        qs = Booking.objects.filter(start_time__gte=window_start, start_time__lte=window_end)

        # If a 'status' field exists, skip cancelled
        field_names = [f.name for f in Booking._meta.get_fields()]
        if "status" in field_names:
            qs = qs.exclude(status="CANCELLED")

        notifier = NotificationService()
        count = 0

        for booking in qs:
            notifier.send_reminder(booking, hours_before=hours)
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {count} reminder(s) for {hours}h window."))
        