# notifications/models.py
#
# Purpose:
# - Record messages sent to clients (confirmation/cancellation).
#
# Design:
# - FK to booking.ClientProfile (not auth.User).
# - 'sent' indicates delivery attempt result.
#
from django.db import models
from booking.models import ClientProfile


class Notification(models.Model):
    user = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)

    def __str__(self) -> str:
        label = getattr(self.user, "name", None) or getattr(self.user, "email", "client")
        return f"Notification to {label} at {self.created_at:%Y-%m-%d %H:%M}"