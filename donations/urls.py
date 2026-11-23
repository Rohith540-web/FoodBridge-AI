from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_donation, name='create_donation'),
    path('history/', views.donation_history, name='donation_history'),
    path('browse/', views.browse_food, name='browse_food'),
    path('details/<int:donation_id>/', views.food_details, name='food_details'),
    path('donate/', views.donate_food_redirect, name='donate_food'),
    path('edit/<int:donation_id>/', views.edit_donation, name='edit_donation'),
    path('delete/<int:donation_id>/', views.delete_donation, name='delete_donation'),
    path('cancel-reservation/<int:donation_id>/', views.cancel_donation_reservation, name='cancel_donation_reservation'),
    path('qr/<int:donation_id>/', views.generate_qr, name='generate_qr'),
    path('qr-code/<int:donation_id>/', views.serve_qr_code, name='serve_qr_code'),
    path('track/<int:donation_id>/', views.track_volunteer, name='track_volunteer'),
]
