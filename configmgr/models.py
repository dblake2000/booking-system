from django.db import models

class SystemSetting(models.Model):
    """
    Simple key/value settings store.
    Example keys:
      - BUSINESS_OPEN (e.g., '09:00')
      - BUSINESS_CLOSE (e.g., '17:00')
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.key}={self.value}"