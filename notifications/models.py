# notifications/models.py
from django.db import models
from booking.models import ClientProfile


class Notification(models.Model):
    """
    Stores delivery of messages (email/SMS/push) to a client profile.
    """
    user = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)

    def __str__(self):
        # ClientProfile likely has name or email, not username
        display = getattr(self.user, "name", None) or getattr(self.user, "email", "client")
        return f"Notification to {display} at {self.created_at:%Y-%m-%d %H:%M}"