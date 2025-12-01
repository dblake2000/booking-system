from django.db import models
from django.utils import timezone

class Staff(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class StaffAvailability(models.Model):
    """
    Time window when a staff member is available.
    For simplicity: store specific date+time ranges.
    """
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="availabilities")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ["staff_id", "start_time"]

    def __str__(self):
        return f"{self.staff.name}: {self.start_time} - {self.end_time}"

    