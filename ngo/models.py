from django.db import models
from django.conf import settings
from donations.models import Donation

class Reservation(models.Model):
    ngo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE, related_name='reservation')
    reserved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donation.food_name} reserved by {self.ngo.username}"
