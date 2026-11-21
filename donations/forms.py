from django import forms
from .models import Donation

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['food_name', 'category', 'quantity', 'preparation_time', 'pickup_deadline', 'pickup_location', 'storage_type', 'special_instructions', 'description', 'image']
        widgets = {
            'preparation_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'pickup_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'storage_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Refrigerated, Room Temp'}),
            'special_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'capture': 'environment', 'accept': 'image/*'}),
        }
