from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, DonorProfile, NgoProfile, VolunteerProfile

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'role', 'phone_number', 'address')

class DonorProfileForm(forms.ModelForm):
    class Meta:
        model = DonorProfile
        fields = ('donor_type', 'organization_name', 'contact_details', 'food_safety_license')

class NgoProfileForm(forms.ModelForm):
    class Meta:
        model = NgoProfile
        fields = ('organization_name', 'registration_number', 'service_area', 'contact_person', 'organization_description', 'capacity')

class VolunteerProfileForm(forms.ModelForm):
    class Meta:
        model = VolunteerProfile
        fields = ('emergency_contact', 'vehicle_type', 'vehicle_details', 'availability')
