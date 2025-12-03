# notifications/models.py
from django.db import models

class Notification(models.Model):
    user = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)

def __str__(self):
        return f"Notification to {self.user.name} at {self.created_at}"
