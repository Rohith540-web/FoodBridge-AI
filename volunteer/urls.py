from django.urls import path
from . import views

urlpatterns = [
    path('deliveries/', views.volunteer_deliveries, name='volunteer_deliveries'),
    path('accept/<int:reservation_id>/', views.accept_delivery, name='accept_delivery'),
    path('cancel/<int:delivery_id>/', views.cancel_delivery, name='cancel_delivery'),
    path('navigation/<int:delivery_id>/', views.navigation, name='volunteer_navigation'),
    path('scan-pickup/<int:delivery_id>/', views.pickup_qr_scanner, name='pickup_qr_scanner'),
    path('scan-delivery/<int:delivery_id>/', views.delivery_qr_scanner, name='delivery_qr_scanner'),
    path('certificate/<int:delivery_id>/', views.delivery_success, name='delivery_success'),
]
