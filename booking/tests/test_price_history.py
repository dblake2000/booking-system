# booking/tests/test_price_history.py

from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from booking.models import Service, PriceHistory


class PriceHistoryTests(TestCase):
    def setUp(self):
        # DRF test client
        self.client = APIClient()

        # Create a sample service
        self.service = Service.objects.create(
            name="Silk Press",
            description="Test service",
            duration_minutes=60,
            price=Decimal("80.00"),
            active=True,
        )

    def test_price_change_creates_history(self):
        # Sanity: no history yet
        self.assertEqual(PriceHistory.objects.count(), 0)

        # PATCH price to a new value via API (mimics user updating price)
        url = f"/api/services/{self.service.id}/"
        resp = self.client.patch(
            url,
            data={"price": "85.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        # Now we should have one PriceHistory entry
        self.assertEqual(PriceHistory.objects.count(), 1)
        ph = PriceHistory.objects.first()
        self.assertEqual(ph.service.id, self.service.id)
        self.assertEqual(ph.old_price, Decimal("80.00"))
        self.assertEqual(ph.new_price, Decimal("85.00"))

    def test_no_history_when_price_unchanged(self):
        # PATCH duration only; price should remain the same
        url = f"/api/services/{self.service.id}/"
        resp = self.client.patch(
            url,
            data={"duration_minutes": 90},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        # No history should be created because price didn't change
        self.assertEqual(PriceHistory.objects.count(), 0)