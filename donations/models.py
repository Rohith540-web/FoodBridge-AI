from django.db import models
from django.conf import settings

class Donation(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('AVAILABLE', 'Available'),
        ('RESERVED', 'Reserved'),
        ('PICKED_UP', 'Picked Up'),
        ('DELIVERED', 'Delivered'),
        ('EXPIRED', 'Expired'),
    )

    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='donations')
    food_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    quantity = models.CharField(max_length=100) # e.g., '5 kg', '20 meals'
    preparation_time = models.DateTimeField()
    pickup_deadline = models.DateTimeField()
    pickup_location = models.TextField()
    storage_type = models.CharField(max_length=255)
    special_instructions = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='donations/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # AI Predictions
    freshness_score = models.FloatField(null=True, blank=True)
    demand_score = models.FloatField(null=True, blank=True)
    priority_score = models.FloatField(null=True, blank=True)
    
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"{self.food_name} by {self.donor.username}"
