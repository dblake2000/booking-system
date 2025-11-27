from django.db import models

# --- CLIENT MODEL ---
class ClientProfile(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


# --- SERVICE MODEL ---
class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} (${self.price})"


# --- STAFF MODEL ---
class Staff(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# --- BOOKING MODEL ---
class Booking(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.client.name} → {self.service.name} on {self.start_time.strftime('%Y-%m-%d %H:%M')}"