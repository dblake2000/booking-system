# booking/services/price_display.py
#
# Feature 7.0: Price Display
# Team Owner: Nishaun Lawrence
#
# Purpose:
# - Provide transparency to clients about service costs
# - Display comprehensive service information before booking
# - Enable informed decision-making

from decimal import Decimal, InvalidOperation


class PriceDisplayService:
    """
    Handles all price display operations for the public-facing catalog.
    
    System Requirements (SRS Feature 7.0):
    1. Retrieve and display all active services with prices and durations
    2. Format prices consistently (currency symbol + 2 decimals)
    3. Display service name, price, and duration together
    4. Allow viewing without login/authentication
    5. Auto-update displayed prices when admin modifies them
    6. Provide filtering/sorting by price, duration, service type
    """
    
    @staticmethod
    def get_service_catalog(service_queryset):
        """
        System Requirement 1 & 3: Retrieve all active services with complete information.
        
        Args:
            service_queryset: Django QuerySet of Service objects
            
        Returns:
            list: List of dictionaries containing service details
        """
        catalog = []
        
        for service in service_queryset:
            catalog.append({
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'price': str(service.price),
                'price_formatted': PriceDisplayService.format_price(service.price),
                'duration_minutes': service.duration_minutes,
                'display_text': PriceDisplayService.format_service_display(service),
            })
        
        return catalog
    
    @staticmethod
    def format_price(price, currency_symbol='$'):
        """
        System Requirement 2: Format prices consistently using currency symbol 
        and exactly two decimal places.
        
        Args:
            price: Price value (Decimal, float, int, or string)
            currency_symbol: Currency symbol to prepend (default: '$')
            
        Returns:
            str: Formatted price (e.g., "$25.00")
        """
        try:
            price_decimal = Decimal(str(price))
            return f"{currency_symbol}{price_decimal:.2f}"
        except (ValueError, TypeError, InvalidOperation):
            return f"{currency_symbol}0.00"
    
    @staticmethod
    def format_service_display(service):
        """
        System Requirement 3: Display service name, price, and duration together
        in a clear, readable format.
        
        Args:
            service: Service model instance
            
        Returns:
            str: Complete display text (e.g., "Haircut — $25.00 • 60 min")
        """
        price_str = PriceDisplayService.format_price(service.price)
        return f"{service.name} — {price_str} • {service.duration_minutes} min"
    
    @staticmethod
    def format_duration(duration_minutes):
        """
        Format duration in a user-friendly way.
        
        Args:
            duration_minutes: Duration in minutes
            
        Returns:
            str: Formatted duration (e.g., "60 min" or "1h 30min")
        """
        if duration_minutes < 60:
            return f"{duration_minutes} min"
        
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        
        if minutes == 0:
            return f"{hours}h"
        
        return f"{hours}h {minutes}min"
    
    @staticmethod
    def filter_by_price_range(service_queryset, min_price=None, max_price=None):
        """
        System Requirement 6: Filter services by price range to help clients
        find services within their budget.
        
        Args:
            service_queryset: Django QuerySet of Service objects
            min_price: Minimum price (optional)
            max_price: Maximum price (optional)
            
        Returns:
            QuerySet: Filtered services
        """
        if min_price is not None:
            try:
                min_price_decimal = Decimal(str(min_price))
                service_queryset = service_queryset.filter(price__gte=min_price_decimal)
            except (ValueError, InvalidOperation):
                pass  # Ignore invalid min_price
        
        if max_price is not None:
            try:
                max_price_decimal = Decimal(str(max_price))
                service_queryset = service_queryset.filter(price__lte=max_price_decimal)
            except (ValueError, InvalidOperation):
                pass  # Ignore invalid max_price
        
        return service_queryset
    
    @staticmethod
    def filter_by_duration_range(service_queryset, min_duration=None, max_duration=None):
        """
        System Requirement 6: Filter services by duration range.
        
        Args:
            service_queryset: Django QuerySet of Service objects
            min_duration: Minimum duration in minutes (optional)
            max_duration: Maximum duration in minutes (optional)
            
        Returns:
            QuerySet: Filtered services
        """
        if min_duration is not None:
            service_queryset = service_queryset.filter(duration_minutes__gte=min_duration)
        
        if max_duration is not None:
            service_queryset = service_queryset.filter(duration_minutes__lte=max_duration)
        
        return service_queryset
    
    @staticmethod
    def sort_services(service_queryset, sort_by='name', ascending=True):
        """
        System Requirement 6: Sort services by various criteria.
        
        Args:
            service_queryset: Django QuerySet of Service objects
            sort_by: Field to sort by ('name', 'price', 'duration')
            ascending: Sort order (True for ascending, False for descending)
            
        Returns:
            QuerySet: Sorted services
        """
        valid_sort_fields = {
            'name': 'name',
            'price': 'price',
            'duration': 'duration_minutes',
        }
        
        field = valid_sort_fields.get(sort_by, 'name')
        
        if not ascending:
            field = f'-{field}'
        
        return service_queryset.order_by(field)
    
    @staticmethod
    def get_price_summary_stats(service_queryset):
        """
        Get summary statistics about pricing across all services.
        Useful for displaying price ranges to users.
        
        Args:
            service_queryset: Django QuerySet of Service objects
            
        Returns:
            dict: Summary statistics
        """
        from django.db.models import Min, Max, Avg, Count
        
        stats = service_queryset.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price'),
            count=Count('id'),
        )
        
        return {
            'min_price': PriceDisplayService.format_price(stats['min_price'] or 0),
            'max_price': PriceDisplayService.format_price(stats['max_price'] or 0),
            'avg_price': PriceDisplayService.format_price(stats['avg_price'] or 0),
            'total_services': stats['count'],
        }
