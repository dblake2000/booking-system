"""
seed_services.py
----------------
Seeds (creates or updates) the service catalog with real names/prices from the
business flyers. You can run this any time; it will upsert by unique name.

Usage:
    python manage.py seed_services
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from booking.models import Service


CATALOG = [
    # Knotless Braids & Senegalese Twists
    {"name": "Knotless Braids - Jumbo",   "description": "Knotless/Jumbo",   "duration_minutes": 240, "price": Decimal("5500.00")},
    {"name": "Knotless Braids - Large",   "description": "Knotless/Large",   "duration_minutes": 300, "price": Decimal("6500.00")},
    {"name": "Knotless Braids - Medium",  "description": "Knotless/Medium",  "duration_minutes": 360, "price": Decimal("7500.00")},
    {"name": "Knotless Braids - Small",   "description": "Knotless/Small",   "duration_minutes": 420, "price": Decimal("8500.00")},

    # Stitch Braids
    {"name": "Stitch Braids - 6-8",       "description": "Stitch Braids",    "duration_minutes": 120, "price": Decimal("5000.00")},
    {"name": "Stitch Braids - 10-14",     "description": "Stitch Braids",    "duration_minutes": 150, "price": Decimal("6000.00")},
    {"name": "Stitch Braids - 14-20",     "description": "Stitch Braids",    "duration_minutes": 180, "price": Decimal("7000.00")},

    # Natural Hair
    {"name": "Cornrows",                   "description": "Natural hair",     "duration_minutes": 90,  "price": Decimal("2500.00")},
    {"name": "Twists (Natural Hair)",      "description": "Natural hair",     "duration_minutes": 90,  "price": Decimal("2000.00")},
    {"name": "Single Plaits (Natural)",    "description": "Natural hair",     "duration_minutes": 120, "price": Decimal("3000.00")},

    # Extras
    {"name": "Blow‑dry hair",              "description": "Extra",            "duration_minutes": 30,  "price": Decimal("500.00")},
    {"name": "Extra length add‑on",        "description": "Extra",            "duration_minutes": 0,   "price": Decimal("500.00")},
    {"name": "Add Curly Hair (boho)",      "description": "Extra (boho)",     "duration_minutes": 0,   "price": Decimal("1500.00")},

    # Take Down Service (from the separate flyer)
    {"name": "Take Down - Jumbo",          "description": "Detangle + large braids", "duration_minutes": 120, "price": Decimal("2500.00")},
    {"name": "Take Down - Large",          "description": "Detangle + large braids", "duration_minutes": 150, "price": Decimal("3000.00")},
    {"name": "Take Down - Medium",         "description": "Detangle + large braids", "duration_minutes": 180, "price": Decimal("3500.00")},
    {"name": "Take Down - Small",          "description": "Detangle + large braids", "duration_minutes": 210, "price": Decimal("4000.00")},
]


class Command(BaseCommand):
    help = "Seed or update the service catalog with real prices."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for item in CATALOG:
            svc, is_created = Service.objects.get_or_create(
                name=item["name"],
                defaults={
                    "description": item["description"],
                    "duration_minutes": item["duration_minutes"],
                    "price": item["price"],
                    "active": True,
                },
            )
            if is_created:
                created += 1
            else:
                changed = False
                if svc.description != item["description"]:
                    svc.description = item["description"]; changed = True
                if svc.duration_minutes != item["duration_minutes"]:
                    svc.duration_minutes = item["duration_minutes"]; changed = True
                if svc.price != item["price"]:
                    svc.price = item["price"]; changed = True
                if not svc.active:
                    svc.active = True; changed = True
                if changed:
                    svc.save()
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Seed complete. Created={created}, Updated={updated}"))