from django.test import TestCase
from django.core import mail
from django.contrib.auth.models import User
from booking.models import Booking

class NotificationTests(TestCase):

    def test_email_sent_when_booking_confirmed(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass123"
        )

        booking = Booking.objects.create(
            user=user,
            date="2025-12-01",
            status="pending"
        )

        # Simulate update to confirmed
        booking.status = "confirmed"
        booking.save()

        # Email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("confirmed", mail.outbox[0].body)
