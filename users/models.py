from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('DONOR', 'Donor'),
        ('NGO', 'NGO'),
        ('VOLUNTEER', 'Volunteer'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='DONOR')
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    address = models.TextField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    # Override email to be unique and required
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class DonorProfile(models.Model):
    DONOR_TYPES = (
        ('Restaurant', 'Restaurant'),
        ('Hotel', 'Hotel'),
        ('Hostel', 'Hostel'),
        ('Marriage Hall', 'Marriage Hall'),
        ('Event Organizer', 'Event Organizer'),
        ('Individual', 'Individual'),
    )
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='donor_profile')
    donor_type = models.CharField(max_length=50, choices=DONOR_TYPES, default='Restaurant')
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    contact_details = models.TextField(blank=True, null=True)
    license_image = models.ImageField(upload_to='restaurant_licenses/', blank=True, null=True)
    food_safety_license = models.CharField(max_length=255, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.organization_name if self.organization_name else self.user.username

class NgoProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='ngo_profile')
    organization_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100)
    service_area = models.CharField(max_length=255, blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    organization_description = models.TextField(blank=True, null=True)
    registration_certificate = models.ImageField(upload_to='ngo_certificates/', blank=True, null=True)
    capacity = models.CharField(max_length=100, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.organization_name

class VolunteerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='volunteer_profile')
    emergency_contact = models.CharField(max_length=50, blank=True, null=True)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    vehicle_details = models.CharField(max_length=255, blank=True, null=True)
    government_id = models.ImageField(upload_to='volunteer_ids/', blank=True, null=True)
    photo = models.ImageField(upload_to='volunteer_photos/', blank=True, null=True)
    availability = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    # Volunteer Trust System
    rating = models.FloatField(default=5.0)
    trust_score = models.IntegerField(default=100)
    successful_deliveries = models.IntegerField(default=0)
    late_deliveries = models.IntegerField(default=0)
    cancelled_deliveries = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Volunteer: {self.user.username}"

class OTPVerification(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_valid(self):
        # OTP is valid for 10 minutes
        return self.created_at >= timezone.now() - timedelta(minutes=10)
