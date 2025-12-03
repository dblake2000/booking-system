from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from notifications.models import Notification
from booking.models import Booking 

@receiver(post_save, sender=Booking)
def send_booking_confirmation_email(sender, instance, created, **kwargs):
    """
    Send an email and create a Notification when a booking status is confirmed.
    """
    
    if instance.status == "confirmed":
        # 1. CORRECT: Use client_profile to refer to the ClientProfile object
        client_profile = instance.client
        
        # 2. CORRECT: Use instance.start_time and client_profile.name
        booking_time_str = instance.start_time.strftime('%Y-%m-%d at %H:%M')
        
        message = (
            f"Hi {client_profile.name}, your booking for the "
            f"{instance.service.name} service on {booking_time_str} "
            f"has been confirmed!"
        )

        # 3. CRITICAL CORRECTION (ASSUMPTION): 
        # The 'user' field on your Notification model must accept the ClientProfile instance.
        # If your Notification model FK is called 'client', you must change 'user=client_profile'
        # If the FK is to the standard Django User, this logic is incorrect entirely.
        
        # Assuming Notification.user is a ForeignKey to ClientProfile:
        Notification.objects.create(
            user=client_profile, 
            message=message,
            sent=True
        )

        # 4. CORRECT: Use client_profile.email
        send_mail(
            subject="Booking Confirmation",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[client_profile.email],
            fail_silently=False,
        )