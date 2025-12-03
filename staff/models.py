# staff/models.py
from django.db import models

class StaffAvailability(models.Model):
    """
    Time window when a staff member is available.
    Points to booking.Staff to avoid having two Staff models.
    """
    staff = models.ForeignKey(
        "booking.Staff",                 # ← reference booking app model
        on_delete=models.CASCADE,
        related_name="availabilities",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ["staff_id", "start_time"]

    def __str__(self):
        return f"{self.staff.name}: {self.start_time} - {self.end_time}"