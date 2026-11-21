from django.db import models
from django.conf import settings
from donations.models import Donation

class Delivery(models.Model):
    STATUS_CHOICES = (
        ('ASSIGNED', 'Assigned'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
    )
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deliveries')
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE, related_name='delivery')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ASSIGNED')
    assigned_at = models.DateTimeField(auto_now_add=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Delivery for {self.donation.food_name} by {self.volunteer.username}"
