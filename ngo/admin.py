from django.contrib import admin
from .models import Reservation

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('donation', 'ngo', 'reserved_at')
    search_fields = ('donation__food_name', 'ngo__username')
