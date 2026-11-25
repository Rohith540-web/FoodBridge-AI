from django.urls import path
from . import views

urlpatterns = [
    path('map/', views.ngo_map_view, name='ngo_map_view'),
    path('reserve/<int:donation_id>/', views.reserve_donation, name='reserve_donation'),
    path('cancel-reservation/<int:reservation_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('assign-volunteer/<int:reservation_id>/', views.assign_volunteer, name='assign_volunteer'),
    path('reservations/', views.my_reservations, name='ngo_reservations'),
    path('pickup/<int:donation_id>/', views.confirm_pickup, name='confirm_pickup'),
    path('track/<int:donation_id>/', views.ngo_track_volunteer, name='ngo_track_volunteer'),
    path('qr-scanner/<int:donation_id>/', views.qr_scanner, name='ngo_qr_scanner'),
]
