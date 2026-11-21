from django.contrib import admin
from .models import Donation

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('food_name', 'donor', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('food_name', 'donor__username', 'pickup_location')
