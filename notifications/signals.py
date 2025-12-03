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
        client_profile = instance.client
        booking_time_str = instance.start_time.strftime('%Y-%m-%d at %H:%M')
        
        message = (
            f"Hi {client_profile.name}, your booking for the "
            f"{instance.service.name} service on {booking_time_str} "
            f"has been confirmed!"
        )

        Notification.objects.create(
            user=client_profile, 
            message=message,
            sent=True
        )

        send_mail(
            subject="Booking Confirmation",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[client_profile.email],
            fail_silently=False,
        )
