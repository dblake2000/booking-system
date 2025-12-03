# booking/services/price_management.py
#
# Feature 6.0: Price Management
# Team Owner: Nishaun Lawrence
#
# Purpose:
# - Allow authorized users to modify service prices
# - Maintain service history and preserve booking prices
# - Validate price changes and log audit trail

from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, InvalidOperation


class PriceManagementService:
    """
    Handles all price management operations for services.
    
    System Requirements (SRS Feature 6.0):
    1. Secure interface accessible only to admin users
    2. Display current price alongside edit field
    3. Validate new price is positive and > 0
    4. Update price immediately, apply only to future bookings
    5. Log all price changes with timestamp, user, old/new price
    6. Display updated price within 30 seconds
    """
    
    @staticmethod
    def validate_price(price):
        """
        System Requirement 3: Validate that new price is positive and greater than zero.
        
        Args:
            price: Price value to validate (can be string, int, float, or Decimal)
            
        Returns:
            Decimal: Valid price as Decimal object
            
        Raises:
            ValidationError: If price is invalid
        """
        try:
            price_decimal = Decimal(str(price))
            
            if price_decimal <= 0:
                raise ValidationError(
                    "Price must be greater than zero. "
                    f"Received: {price_decimal}"
                )
            
            # Check reasonable max (e.g., $999,999.99)
            if price_decimal > Decimal('999999.99'):
                raise ValidationError(
                    "Price exceeds maximum allowed value of $999,999.99. "
                    f"Received: {price_decimal}"
                )
            
            return price_decimal
            
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValidationError(
                f"Invalid price format. Price must be a positive number. "
                f"Received: {price}. Error: {str(e)}"
            )
    
    @staticmethod
    def get_current_price(service):
        """
        System Requirement 2: Retrieve current price for display alongside edit field.
        
        Args:
            service: Service model instance
            
        Returns:
            Decimal: Current price of the service
        """
        return service.price
    
    @staticmethod
    def update_service_price(service, new_price, admin_user=None):
        """
        System Requirement 4: Update service price immediately.
        
        Note: This method updates the price in the database. Future bookings
        will use the new price, while existing bookings retain their original
        price (enforced by the booking system storing price at booking time).
        
        Args:
            service: Service model instance to update
            new_price: New price value
            admin_user: User making the change (for logging)
            
        Returns:
            dict: Contains old_price, new_price, success status
            
        Raises:
            ValidationError: If price validation fails
        """
        old_price = service.price
        
        # Validate new price (Requirement 3)
        validated_price = PriceManagementService.validate_price(new_price)
        
        # Update the service
        service.price = validated_price
        service.save()
        
        # Log the change (Requirement 5)
        # Note: Actual logging implementation would go here
        # For now, we'll return the change details
        change_log = {
            'success': True,
            'service_id': service.id,
            'service_name': service.name,
            'old_price': str(old_price),
            'new_price': str(validated_price),
            'changed_by': admin_user.username if admin_user else 'system',
            'timestamp': timezone.now().isoformat(),
        }
        
        return change_log
    
    @staticmethod
    def format_price_for_display(price):
        """
        Format price consistently with currency symbol and two decimal places.
        
        Args:
            price: Price value (Decimal, float, or string)
            
        Returns:
            str: Formatted price string (e.g., "$25.00")
        """
        try:
            price_decimal = Decimal(str(price))
            return f"${price_decimal:.2f}"
        except (ValueError, InvalidOperation):
            return "$0.00"
    
    @staticmethod
    def get_price_change_summary(service, new_price):
        """
        Get a summary of what will change before applying the price update.
        Useful for confirmation dialogs.
        
        Args:
            service: Service instance
            new_price: Proposed new price
            
        Returns:
            dict: Summary of changes
        """
        current_price = service.price
        validated_price = PriceManagementService.validate_price(new_price)
        
        return {
            'service_name': service.name,
            'current_price': PriceManagementService.format_price_for_display(current_price),
            'new_price': PriceManagementService.format_price_for_display(validated_price),
            'difference': PriceManagementService.format_price_for_display(validated_price - current_price),
            'percent_change': float((validated_price - current_price) / current_price * 100),
        }
