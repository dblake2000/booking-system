# booking/management/commands/test_email.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Send a one-off test email using current EMAIL_* settings."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Destination email address")
        parser.add_argument("--subject", default="Test Email — Booking System")
        parser.add_argument("--body", default="This is a random test email from Django.")

    def handle(self, *args, **opts):
        to_addr = opts["to"]
        subject = opts["subject"]
        body = opts["body"]

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_addr],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Sent test email to {to_addr}"))