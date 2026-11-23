from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, DonorProfile, NgoProfile, VolunteerProfile

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'role', 'phone_number', 'address')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Only block if an ACTIVE user already exists with this username
        if CustomUser.objects.filter(username=username, is_active=True).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Only block if an ACTIVE user already exists with this email
        if email and CustomUser.objects.filter(email__iexact=email, is_active=True).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Only block if an ACTIVE user already exists with this phone number
        if phone and CustomUser.objects.filter(phone_number=phone, is_active=True).exists():
            raise ValidationError("A user with that phone number already exists.")
        return phone

    def validate_unique(self):
        # Exclude unverified (is_active=False) registrations from unique constraints
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            cleaned_errors = {}
            for field, errs in e.message_dict.items():
                if field == 'username':
                    val = self.cleaned_data.get('username')
                    if CustomUser.objects.filter(username=val, is_active=True).exists():
                        cleaned_errors[field] = errs
                elif field == 'email':
                    val = self.cleaned_data.get('email')
                    if CustomUser.objects.filter(email__iexact=val, is_active=True).exists():
                        cleaned_errors[field] = errs
                elif field == 'phone_number':
                    val = self.cleaned_data.get('phone_number')
                    if CustomUser.objects.filter(phone_number=val, is_active=True).exists():
                        cleaned_errors[field] = errs
                else:
                    cleaned_errors[field] = errs
            if cleaned_errors:
                raise ValidationError(cleaned_errors)

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
