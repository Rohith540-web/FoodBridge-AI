"""
URL configuration for foodbridge_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
import re
from io import BytesIO
import qrcode
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as django_serve
from django.http import HttpResponse, FileResponse
from dashboard.views import landing_page


def smart_media_serve(request, path, **kwargs):
    """
    Serves media files if they exist on disk.
    If ephemeral storage wiped the file (common on Render free tier):
    - For QR codes: dynamically regenerates the QR code PNG so it NEVER returns 404.
    - For donation images: serves the appropriate static food placeholder.
    """
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return django_serve(request, path, **kwargs)

    # Missing QR code fallback
    if path.startswith('qr_codes/') or 'qr_' in path:
        match = re.search(r'(\d+)\.png$', path)
        donation_id = match.group(1) if match else "1"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"Donation_ID:{donation_id}, FoodBridge Verified")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return HttpResponse(buf.getvalue(), content_type="image/png")

    # Missing food donation image fallback
    fallback_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'food', 'meals.jpg')
    p_lower = path.lower()
    if 'biryani' in p_lower or 'briyani' in p_lower:
        biryani_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'food', 'biryani.jpg')
        if os.path.exists(biryani_path):
            fallback_path = biryani_path
    elif 'bakery' in p_lower or 'bread' in p_lower:
        bakery_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'food', 'bakery.jpg')
        if os.path.exists(bakery_path):
            fallback_path = bakery_path
    elif 'beverage' in p_lower or 'juice' in p_lower:
        bev_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'food', 'beverages.jpg')
        if os.path.exists(bev_path):
            fallback_path = bev_path

    if os.path.exists(fallback_path):
        return FileResponse(open(fallback_path, 'rb'), content_type="image/jpeg")

    return django_serve(request, path, **kwargs)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('donations/', include('donations.urls')),
    path('ngo/', include('ngo.urls')),
    path('volunteer/', include('volunteer.urls')),
    path('notifications/', include('notifications.urls')),
    path('', landing_page, name='landing'),
    re_path(r'^media/(?P<path>.*)$', smart_media_serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
