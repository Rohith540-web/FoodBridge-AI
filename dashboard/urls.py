from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('admin/', views.admin_home, name='admin_home'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/<str:action>/', views.admin_user_action, name='admin_user_action'),
    path('admin/deliveries/', views.admin_deliveries, name='admin_deliveries'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
]
