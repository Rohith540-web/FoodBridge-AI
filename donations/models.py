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
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    @property
    def get_latitude(self):
        if self.latitude:
            return self.latitude
        try:
            if self.donor and self.donor.latitude:
                return self.donor.latitude
        except Exception:
            pass
        loc = (self.pickup_location or '').lower()
        if 'thiruvallur' in loc or 'tiruvallur' in loc:
            return 13.1433
        elif 'saveetha' in loc or 'thandalam' in loc:
            return 13.0280
        elif 'sriperumbudur' in loc:
            return 12.9675
        elif 'mannur' in loc:
            return 13.0199
        elif 'chennai' in loc or 'madras' in loc:
            return 13.0827
        return 13.0827

    @property
    def get_longitude(self):
        if self.longitude:
            return self.longitude
        try:
            if self.donor and self.donor.longitude:
                return self.donor.longitude
        except Exception:
            pass
        loc = (self.pickup_location or '').lower()
        if 'thiruvallur' in loc or 'tiruvallur' in loc:
            return 79.9079
        elif 'saveetha' in loc or 'thandalam' in loc:
            return 80.0163
        elif 'sriperumbudur' in loc:
            return 79.9436
        elif 'mannur' in loc:
            return 79.9846
        elif 'chennai' in loc or 'madras' in loc:
            return 80.2707
        return 80.2707

    @property
    def image_url(self):
        if self.image:
            try:
                if hasattr(self.image, 'storage') and self.image.storage.exists(self.image.name):
                    return self.image.url
            except Exception:
                pass
        cat = (self.category or '').lower()
        name = (self.food_name or '').lower()
        if 'bakery' in cat or 'bread' in name or 'pastr' in name:
            return '/static/images/food/bakery.jpg'
        elif 'juice' in name or 'beverag' in cat or 'snack' in cat:
            return '/static/images/food/beverages.jpg'
        elif 'biryani' in name or 'briyani' in name or 'rice' in name:
            return '/static/images/food/biryani.jpg'
        return '/static/images/food/meals.jpg'

    @property
    def qr_code_url(self):
        return f"/donations/qr-code/{self.id}/"

    def __str__(self):
        return f"{self.food_name} by {self.donor.username}"
