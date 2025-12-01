from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from booking.models import (
    Service,
    ClientProfile,
    Staff,
    Booking,
    PriceHistory,
)


class PriceHistoryTests(TestCase):
    def setUp(self):
        # DRF client
        self.client = APIClient()

        # Create a sample service
        self.service = Service.objects.create(
            name="Silk Press",
            description="Test service",
            duration_minutes=60,
            price=Decimal("80.00"),
            active=True,
        )

        # Create a staff user and log in (needed for write operations)
        self.staff_user = User.objects.create_user(
            username="staff1",
            password="Password123!",
            email="staff1@example.com",
            is_staff=True,  # IMPORTANT: staff can update services
        )
        # Log in the staff user in the test client (session-based)
        logged_in = self.client.login(username="staff1", password="Password123!")
        self.assertTrue(logged_in, "Failed to log in test staff user")

    def test_price_change_creates_history(self):
        # Sanity: no history yet
        self.assertEqual(PriceHistory.objects.count(), 0)

        # PATCH price to a new value via API (staff-only write)
        url = f"/api/services/{self.service.id}/"
        resp = self.client.patch(
            url,
            data={"price": "85.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Unexpected status: {resp.status_code} body={resp.content}")

        # Now we should have one PriceHistory entry
        self.assertEqual(PriceHistory.objects.count(), 1)
        ph = PriceHistory.objects.first()
        self.assertEqual(ph.service.id, self.service.id)
        self.assertEqual(ph.old_price, Decimal("80.00"))
        self.assertEqual(ph.new_price, Decimal("85.00"))

    def test_no_history_when_price_unchanged(self):
        # PATCH duration only (no price change)
        url = f"/api/services/{self.service.id}/"
        resp = self.client.patch(
            url,
            data={"duration_minutes": 90},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, f"Unexpected status: {resp.status_code} body={resp.content}")

        # No history should be created because price didn't change
        self.assertEqual(PriceHistory.objects.count(), 0)

    def test_anonymous_can_read_services(self):
        """
        Bonus: ensure read endpoints are open (GET allowed for everyone).
        """
        anon = APIClient()
        resp = anon.get("/api/services/")
        self.assertEqual(resp.status_code, 200)


class BookingRulesTests(TestCase):
    def setUp(self):
        # DRF client
        self.api = APIClient()

        # Service (active, valid price/duration)
        self.service = Service.objects.create(
            name="Cut",
            description="",
            duration_minutes=60,
            price=Decimal("50.00"),
            active=True,
        )

        # Staff (IMPORTANT: this is booking.models.Staff to match Booking.staff FK)
        self.staff = Staff.objects.create(
            name="Stylist A",
            email="stylista@example.com",
            role="Stylist",
        )

        # Client user + profile
        self.client_user = User.objects.create_user(
            username="client1",
            password="Password123!",
            email="client1@example.com",
        )
        self.client_profile = ClientProfile.objects.create(
            user=self.client_user,
            name="Client One",
            email="client1@example.com",
        )

        # Log in as client (session auth) for booking endpoints
        logged_in = self.api.login(username="client1", password="Password123!")
        self.assertTrue(logged_in, "Failed to log in test client user")

    def _create_future_iso(self, hours=24):
        return (timezone.now() + timedelta(hours=hours)).replace(microsecond=0).isoformat()

    def test_cannot_book_in_past(self):
        past_iso = (timezone.now() - timedelta(hours=1)).replace(microsecond=0).isoformat()

        payload = {
            "client": self.client_profile.id,   # perform_create may force this, but keep for clarity
            "service": self.service.id,
            "staff": self.staff.id,
            "start_time": past_iso,
            "notes": "",
        }
        r = self.api.post("/api/bookings/", payload, format="json")
        self.assertEqual(r.status_code, 400, f"Unexpected: {r.status_code} body={r.content}")

    def test_cannot_double_book_same_staff_time(self):
        # First booking at +24h
        start_iso = self._create_future_iso(hours=24)

        payload = {
            "client": self.client_profile.id,
            "service": self.service.id,
            "staff": self.staff.id,
            "start_time": start_iso,
            "notes": "",
        }
        r1 = self.api.post("/api/bookings/", payload, format="json")
        self.assertEqual(r1.status_code, 201, f"Unexpected: {r1.status_code} body={r1.content}")
        b1_id = r1.json().get("id")
        self.assertIsNotNone(b1_id)

        # Second booking: same staff and same start time should fail
        payload2 = {
            "client": self.client_profile.id,
            "service": self.service.id,
            "staff": self.staff.id,
            "start_time": start_iso,  # same time
            "notes": "",
        }
        r2 = self.api.post("/api/bookings/", payload2, format="json")
        self.assertEqual(r2.status_code, 400, f"Should have blocked double-booking: {r2.status_code} body={r2.content}")

    def test_cannot_cancel_within_2_hours(self):
        # Make a booking at +90 minutes (inside 2-hour cutoff)
        start_iso = self._create_future_iso(hours=1.5)

        payload = {
            "client": self.client_profile.id,
            "service": self.service.id,
            "staff": self.staff.id,
            "start_time": start_iso,
            "notes": "",
        }
        r1 = self.api.post("/api/bookings/", payload, format="json")
        self.assertEqual(r1.status_code, 201, f"Create failed: {r1.status_code} body={r1.content}")
        booking_id = r1.json().get("id")

        # Try to cancel (should fail with 400 because within 2 hours)
        r2 = self.api.post(f"/api/bookings/{booking_id}/cancel/")
        self.assertEqual(r2.status_code, 400, f"Cancel should fail inside cutoff: {r2.status_code} body={r2.content}")