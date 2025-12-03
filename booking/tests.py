from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from decimal import Decimal

from .models import Service
from .services.price_management import PriceManagementService
from .services.price_display import PriceDisplayService


class PriceManagementTests(TestCase):
    """
    Tests for Feature 6.0: Price Management
    Team Owner: Nishaun Lawrence
    """
    
    def setUp(self):
        """Set up test data"""
        self.service = Service.objects.create(
            name="Test Haircut",
            description="A test service",
            duration_minutes=60,
            price=Decimal("50.00")
        )
        
        self.admin_user = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True
        )
    
    def test_validate_valid_price(self):
        """Test that valid prices pass validation"""
        # Test various valid formats
        self.assertEqual(
            PriceManagementService.validate_price("25.00"),
            Decimal("25.00")
        )
        self.assertEqual(
            PriceManagementService.validate_price(50),
            Decimal("50")
        )
        self.assertEqual(
            PriceManagementService.validate_price(Decimal("100.99")),
            Decimal("100.99")
        )
    
    def test_validate_price_rejects_zero(self):
        """System Requirement 3: Reject price of zero"""
        with self.assertRaises(ValidationError) as context:
            PriceManagementService.validate_price(0)
        
        self.assertIn("greater than zero", str(context.exception))
    
    def test_validate_price_rejects_negative(self):
        """System Requirement 3: Reject negative prices"""
        with self.assertRaises(ValidationError) as context:
            PriceManagementService.validate_price(-10)
        
        self.assertIn("greater than zero", str(context.exception))
    
    def test_validate_price_rejects_non_numeric(self):
        """System Requirement 3: Reject non-numeric values"""
        with self.assertRaises(ValidationError):
            PriceManagementService.validate_price("abc")
        
        with self.assertRaises(ValidationError):
            PriceManagementService.validate_price("$50.00")
    
    def test_get_current_price(self):
        """System Requirement 2: Retrieve current price"""
        current_price = PriceManagementService.get_current_price(self.service)
        self.assertEqual(current_price, Decimal("50.00"))
    
    def test_update_service_price(self):
        """System Requirement 4: Update service price"""
        old_price = self.service.price
        
        result = PriceManagementService.update_service_price(
            service=self.service,
            new_price="75.00",
            admin_user=self.admin_user
        )
        
        # Refresh from database
        self.service.refresh_from_db()
        
        # Check price was updated
        self.assertEqual(self.service.price, Decimal("75.00"))
        
        # Check result contains change log
        self.assertTrue(result['success'])
        self.assertEqual(result['old_price'], str(old_price))
        self.assertEqual(result['new_price'], "75.00")
        self.assertEqual(result['changed_by'], 'admin')
    
    def test_format_price_for_display(self):
        """System Requirement 2: Format prices consistently"""
        self.assertEqual(
            PriceManagementService.format_price_for_display("25"),
            "$25.00"
        )
        self.assertEqual(
            PriceManagementService.format_price_for_display(Decimal("99.99")),
            "$99.99"
        )
        self.assertEqual(
            PriceManagementService.format_price_for_display("invalid"),
            "$0.00"
        )


class PriceDisplayTests(TestCase):
    """
    Tests for Feature 7.0: Price Display
    Team Owner: Nishaun Lawrence
    """
    
    def setUp(self):
        """Set up test data"""
        self.service1 = Service.objects.create(
            name="Basic Haircut",
            description="Standard haircut",
            duration_minutes=30,
            price=Decimal("25.00")
        )
        
        self.service2 = Service.objects.create(
            name="Premium Haircut",
            description="Premium styling",
            duration_minutes=60,
            price=Decimal("50.00")
        )
        
        self.service3 = Service.objects.create(
            name="Deluxe Treatment",
            description="Full treatment",
            duration_minutes=90,
            price=Decimal("75.00")
        )
    
    def test_get_service_catalog(self):
        """System Requirement 1: Retrieve all services with details"""
        services = Service.objects.all()
        catalog = PriceDisplayService.get_service_catalog(services)
        
        self.assertEqual(len(catalog), 3)
        
        # Check first service has all required fields
        first = catalog[0]
        self.assertIn('id', first)
        self.assertIn('name', first)
        self.assertIn('price', first)
        self.assertIn('price_formatted', first)
        self.assertIn('duration_minutes', first)
        self.assertIn('display_text', first)
    
    def test_format_price_consistent(self):
        """System Requirement 2: Format with currency symbol and 2 decimals"""
        self.assertEqual(
            PriceDisplayService.format_price(25),
            "$25.00"
        )
        self.assertEqual(
            PriceDisplayService.format_price(Decimal("50.5")),
            "$50.50"
        )
        self.assertEqual(
            PriceDisplayService.format_price("99.99"),
            "$99.99"
        )
        self.assertEqual(
            PriceDisplayService.format_price("99.99"),
            "$99.99"
        )
        self.assertEqual(
            PriceDisplayService.format_price("99.99"),
            "$99.99"
        )
        self.assertEqual(
            PriceDisplayService.format_price("99.99"),
            "$99.99"
        )
    
    def test_format_service_display(self):
        """System Requirement 3: Display name, price, and duration together"""
        display = PriceDisplayService.format_service_display(self.service1)
        
        # Should contain all three elements
        self.assertIn("Basic Haircut", display)
        self.assertIn("$25.00", display)
        self.assertIn("30 min", display)
    
    def test_filter_by_price_range(self):
        """System Requirement 6: Filter services by price range"""
        services = Service.objects.all()
        
        # Filter: $20 - $60
        filtered = PriceDisplayService.filter_by_price_range(
            services,
            min_price=20,
            max_price=60
        )
        
        # Should include service1 ($25) and service2 ($50), exclude service3 ($75)
        self.assertEqual(filtered.count(), 2)
        self.assertIn(self.service1, filtered)
        self.assertIn(self.service2, filtered)
        self.assertNotIn(self.service3, filtered)
    
    def test_filter_by_duration_range(self):
        """System Requirement 6: Filter services by duration"""
        services = Service.objects.all()
        
        # Filter: 30-60 minutes
        filtered = PriceDisplayService.filter_by_duration_range(
            services,
            min_duration=30,
            max_duration=60
        )
        
        # Should include service1 (30min) and service2 (60min), exclude service3 (90min)
        self.assertEqual(filtered.count(), 2)
    
    def test_sort_services_by_price(self):
        """System Requirement 6: Sort services by price"""
        services = Service.objects.all()
        
        # Sort ascending
        sorted_asc = PriceDisplayService.sort_services(services, sort_by='price', ascending=True)
        prices_asc = list(sorted_asc.values_list('price', flat=True))
        self.assertEqual(prices_asc, [Decimal('25.00'), Decimal('50.00'), Decimal('75.00')])
        
        # Sort descending
        sorted_desc = PriceDisplayService.sort_services(services, sort_by='price', ascending=False)
        prices_desc = list(sorted_desc.values_list('price', flat=True))
        self.assertEqual(prices_desc, [Decimal('75.00'), Decimal('50.00'), Decimal('25.00')])
    
    def test_get_price_summary_stats(self):
        """Test price summary statistics"""
        services = Service.objects.all()
        stats = PriceDisplayService.get_price_summary_stats(services)
        
        self.assertEqual(stats['min_price'], "$25.00")
        self.assertEqual(stats['max_price'], "$75.00")
        self.assertEqual(stats['total_services'], 3)
        self.assertIn('avg_price', stats)

