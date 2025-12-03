from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone 

# Adjust imports as necessary based on where your models are defined
from notifications.models import Notification
from .models import Booking, ClientProfile 

# --- HELPER FUNCTION TO SEND EMAIL ---
def send_notification_email(subject, body, recipient_email):
    """Generic function to handle email sending."""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception as e:
        # Prints the error to your console if sending fails
        print(f"Error sending email to {recipient_email} (Subject: {subject}): {e}")


# CONFIRMATION SIGNAL FOR EMAIL OPERATIONS
@receiver(post_save, sender=Booking)
def handle_booking_confirmation(sender, instance, created, **kwargs):
    """
    Sends confirmation email and creates notification when status is CONFIRMED.
    This runs on creation OR update.
    """
    
    # Check if the booking is currently CONFIRMED
    if instance.status == "CONFIRMED":
        
        should_send = False
        
        if created:
            # Booking was just created AND its initial status is CONFIRMED
            should_send = True
        else:
            # Booking existed, check if the status field was the one that was updated
            update_fields = kwargs.get('update_fields')
            if update_fields is None or 'status' in update_fields:
                should_send = True
        
        # --- Execute sending logic only if the status change warrants it ---
        if should_send:
            
            client_profile = instance.client
            booking_time_str = instance.start_time.strftime('%Y-%m-%d at %I:%M %p %Z')
            
            # --- Notification Message ---
            client_message = (
                f"Hi {client_profile.name}, your booking for the "
                f"{instance.service.name} service on {booking_time_str} "
                f"has been successfully CONFIRMED!"
            )

            # Create Notification model instance
            Notification.objects.create(
                user=client_profile, 
                message=client_message,
                sent=True
            )

            # Send Email to Client
            send_notification_email(
                subject="Booking Confirmation: Your Appointment is Confirmed!",
                body=client_message,
                recipient_email=client_profile.email
            )


# CANCELLATION SIGNAL FOR EMAIL SENDING
@receiver(post_save, sender=Booking)
def handle_booking_cancellation(sender, instance, created, **kwargs):
    """Sends cancellation emails to Client and Owner when status is CANCELLED."""
    
    # Run logic only if status is CANCELLED
    if instance.status == "CANCELLED":
        
        # Prevent emails on creation if CANCELLED is the default/initial state
        if created:
            return

        client_profile = instance.client
        booking_time_str = instance.start_time.strftime('%Y-%m-%d at %I:%M %p %Z')
        
        # --- Client Cancellation ---
        client_subject = f"Booking #{instance.pk} Has Been Cancelled"
        client_body = (
            f"Dear {client_profile.name},\n\n"
            f"Your appointment for {instance.service.name} on {booking_time_str} "
            f"has been successfully CANCELLED. We hope to see you soon."
        )
        send_notification_email(
            subject=client_subject,
            body=client_body,
            recipient_email=client_profile.email
        )

        # --- Owner/Admin Cancellation Alert ---
        owner_subject = f"ALERT: Booking #{instance.pk} CANCELLATION"
        owner_body = (
            f"Booking ID: #{instance.pk} has been cancelled by the system or staff.\n"
            f"Client: {client_profile.name} ({client_profile.email})\n"
            f"Service: {instance.service.name}\n"
            f"Original Time: {booking_time_str}\n"
            f"Cancellation Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_notification_email(
            subject=owner_subject,
            body=owner_body,
            recipient_email=settings.EMAIL_HOST_USER
        )