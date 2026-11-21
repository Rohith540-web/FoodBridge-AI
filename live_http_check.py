import re
import urllib.request
import urllib.parse
import http.cookiejar
from datetime import timedelta
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodbridge_project.settings')
django.setup()

from django.utils import timezone
from donations.models import Donation
from volunteer.models import Delivery

BASE_URL = "http://127.0.0.1:8000"

class LiveClient:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPRedirectHandler()
        )

    def get(self, path):
        url = BASE_URL + path if path.startswith('/') else path
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            resp = self.opener.open(req)
            return resp.status, resp.read().decode('utf-8', errors='ignore'), resp.geturl()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', errors='ignore'), e.geturl()

    def get_csrf(self, html):
        match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', html)
        if match:
            return match.group(1)
        for cookie in self.cj:
            if cookie.name == 'csrftoken':
                return cookie.value
        return ''

    def post(self, path, data):
        url = BASE_URL + path if path.startswith('/') else path
        encoded = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data=encoded, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': url
        })
        try:
            resp = self.opener.open(req)
            return resp.status, resp.read().decode('utf-8', errors='ignore'), resp.geturl()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', errors='ignore'), e.geturl()

results = []

def record(name, passed, detail=""):
    results.append((name, passed, detail))
    icon = "[PASS]" if passed else "[FAIL]"
    print(f"{icon} {name}: {detail}", flush=True)

print("="*60)
print("   FOODBRIDGE AI - LIVE SERVER (http://127.0.0.1:8000) TEST")
print("="*60, flush=True)

# ---------------------------------------------------------
# 1. PUBLIC PAGES
# ---------------------------------------------------------
client = LiveClient()

status, html, _ = client.get('/')
record("1. Landing Page (/) HTTP 200", status == 200 and 'FoodBridge AI' in html, f"Status: {status}")

status, html, _ = client.get('/users/select-role/')
record("2. Role Selection (/users/select-role/) HTTP 200", status == 200 and 'Donor' in html, f"Status: {status}")

status, html, _ = client.get('/donations/browse/')
record("3. Browse Food (/donations/browse/) HTTP 200", status == 200 and 'Browse Available Food' in html, f"Status: {status}")

status, html, _ = client.get('/donations/browse/?category=meals')
record("4. Category Filter (/donations/browse/?category=meals) HTTP 200", status == 200, f"Status: {status}")

status, html, _ = client.get('/users/login/')
record("5. Login Page (/users/login/) HTTP 200", status == 200 and 'csrfmiddlewaretoken' in html, f"Status: {status}")

# ---------------------------------------------------------
# 2. DONOR LOGIN & ACTIONS
# ---------------------------------------------------------
csrf = client.get_csrf(html)
status, html, final_url = client.post('/users/login/', {
    'username': 'donor_demo',
    'password': 'Pass@1234',
    'csrfmiddlewaretoken': csrf
})
record("6. Donor Login POST", status == 200 and '/dashboard/' in final_url, f"Redirected to: {final_url}")

status, html, _ = client.get('/dashboard/')
record("7. Donor Dashboard HTTP 200", status == 200 and 'Donor Account' in html, f"Status: {status}")

# Create Donation via Live POST
status, html, _ = client.get('/donations/create/')
csrf = client.get_csrf(html)
now = timezone.now()
status, html, final_url = client.post('/donations/create/', {
    'food_name': 'Live Verified Rice Box',
    'category': 'cooked meals',
    'quantity': '15 meals',
    'preparation_time': (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
    'pickup_deadline': (now + timedelta(hours=10)).strftime('%Y-%m-%dT%H:%M'),
    'pickup_location': 'City Shelter Point, Bengaluru',
    'storage_type': 'Heated Box',
    'special_instructions': 'Fragile packaging',
    'description': 'Warm meals for immediate rescue',
    'action': 'submit',
    'csrfmiddlewaretoken': csrf
})
record("8. Donor Add Food Live POST", status == 200 and '/donations/history/' in final_url, f"Result URL: {final_url}")

status, html, _ = client.get('/donations/history/')
record("9. Donor My Listings HTTP 200", status == 200 and 'Live Verified Rice Box' in html, f"Status: {status}")

latest_don = Donation.objects.filter(food_name='Live Verified Rice Box').order_by('-created_at').first()
record("10. AI Scores & QR Code created in DB", latest_don is not None and latest_don.qr_code and latest_don.freshness_score is not None, f"Freshness: {latest_don.freshness_score if latest_don else 'None'}, QR: {bool(latest_don.qr_code) if latest_don else False}")

status, html, _ = client.get(f'/donations/details/{latest_don.id}/')
record("11. Food Details Page HTTP 200", status == 200 and 'Live Verified Rice Box' in html, f"Status: {status}")

# Logout
csrf = client.get_csrf(html)
status, html, _ = client.post('/users/logout/', {'csrfmiddlewaretoken': csrf})
record("12. Donor Logout POST", status == 200, "Logged out successfully")

# ---------------------------------------------------------
# 3. NGO LOGIN & ACTIONS
# ---------------------------------------------------------
ngo_client = LiveClient()
status, html, _ = ngo_client.get('/users/login/')
csrf = ngo_client.get_csrf(html)
status, html, final_url = ngo_client.post('/users/login/', {
    'username': 'ngo_demo',
    'password': 'Pass@1234',
    'csrfmiddlewaretoken': csrf
})
record("13. NGO Login POST", status == 200 and '/dashboard/' in final_url, f"Result URL: {final_url}")

status, html, _ = ngo_client.get('/dashboard/')
record("14. NGO Dashboard HTTP 200", status == 200 and 'NGO Account' in html, f"Status: {status}")

status, html, _ = ngo_client.get('/ngo/map/')
record("15. NGO Map View HTTP 200", status == 200 and 'leaflet' in html.lower(), f"Status: {status}")

# Reserve the donation
status, html, _ = ngo_client.get(f'/donations/details/{latest_don.id}/')
csrf = ngo_client.get_csrf(html)
status, html, final_url = ngo_client.post(f'/ngo/reserve/{latest_don.id}/', {
    'csrfmiddlewaretoken': csrf
})
record("16. NGO Reserve Food Live POST", status == 200 and '/ngo/reservations/' in final_url, f"Result URL: {final_url}")

status, html, _ = ngo_client.get('/ngo/reservations/')
record("17. NGO Reservations Page HTTP 200", status == 200 and 'Live Verified Rice Box' in html, f"Status: {status}")

status, html, _ = ngo_client.get(f'/ngo/track/{latest_don.id}/')
record("18. NGO Track Volunteer Page HTTP 200", status == 200 and 'Delivery Status' in html, f"Status: {status}")

csrf = ngo_client.get_csrf(html)
ngo_client.post('/users/logout/', {'csrfmiddlewaretoken': csrf})

# ---------------------------------------------------------
# 4. VOLUNTEER LOGIN & LIFECYCLE
# ---------------------------------------------------------
vol_delivery = Delivery.objects.filter(donation=latest_don).first()
vol_user = vol_delivery.volunteer.username if vol_delivery else 'volunteer1'

vol_client = LiveClient()
status, html, _ = vol_client.get('/users/login/')
csrf = vol_client.get_csrf(html)
status, html, final_url = vol_client.post('/users/login/', {
    'username': vol_user,
    'password': 'Pass@1234',
    'csrfmiddlewaretoken': csrf
})
record("19. Volunteer Login POST", status == 200 and '/dashboard/' in final_url, f"User: {vol_user}")

status, html, _ = vol_client.get('/dashboard/')
record("20. Volunteer Dashboard HTTP 200", status == 200 and 'Volunteer Account' in html, f"Status: {status}")

status, html, _ = vol_client.get('/volunteer/deliveries/')
record("21. Volunteer Deliveries HTTP 200", status == 200 and 'My Deliveries' in html, f"Status: {status}")

status, html, _ = vol_client.get(f'/volunteer/navigation/{vol_delivery.id}/')
record("22. Volunteer Navigation HTTP 200", status == 200 and 'Live Navigation' in html, f"Status: {status}")

# Scan Pickup QR
status, html, _ = vol_client.get(f'/volunteer/scan-pickup/{vol_delivery.id}/')
csrf = vol_client.get_csrf(html)
status, html, final_url = vol_client.post(f'/volunteer/scan-pickup/{vol_delivery.id}/', {
    'csrfmiddlewaretoken': csrf
})
record("23. Volunteer Pickup QR Scan POST", status == 200 and '/volunteer/deliveries/' in final_url, f"Result URL: {final_url}")

# Scan Delivery QR
status, html, _ = vol_client.get(f'/volunteer/scan-delivery/{vol_delivery.id}/')
csrf = vol_client.get_csrf(html)
status, html, final_url = vol_client.post(f'/volunteer/scan-delivery/{vol_delivery.id}/', {
    'csrfmiddlewaretoken': csrf
})
record("24. Volunteer Delivery QR Scan POST", status == 200 and '/volunteer/certificate/' in final_url, f"Result URL: {final_url}")

status, html, _ = vol_client.get(f'/volunteer/certificate/{vol_delivery.id}/')
record("25. Certificate of Impact HTTP 200", status == 200 and 'Certificate of Impact' in html, f"Status: {status}")

csrf = vol_client.get_csrf(html)
vol_client.post('/users/logout/', {'csrfmiddlewaretoken': csrf})

# ---------------------------------------------------------
# 5. ADMIN ACTIONS & ANALYTICS
# ---------------------------------------------------------
admin_client = LiveClient()
status, html, _ = admin_client.get('/users/login/')
csrf = admin_client.get_csrf(html)
status, html, final_url = admin_client.post('/users/login/', {
    'username': 'admin',
    'password': 'Pass@1234',
    'csrfmiddlewaretoken': csrf
})
record("26. Admin Login POST", status == 200 and '/dashboard/admin/' in final_url, f"Result URL: {final_url}")

status, html, _ = admin_client.get('/dashboard/admin/')
record("27. Admin Dashboard HTTP 200", status == 200 and 'System Overview' in html, f"Status: {status}")

status, html, _ = admin_client.get('/dashboard/admin/users/')
record("28. Admin Manage Users HTTP 200", status == 200 and 'Manage Users' in html, f"Status: {status}")

status, html, _ = admin_client.get('/dashboard/admin/deliveries/')
record("29. Admin Live Deliveries HTTP 200", status == 200 and 'Live Deliveries' in html, f"Status: {status}")

status, html, _ = admin_client.get('/dashboard/admin/analytics/')
record("30. Admin AI Analytics HTTP 200", status == 200 and 'AI Analytics & Impact' in html, f"Status: {status}")

# ---------------------------------------------------------
# 6. NOTIFICATIONS
# ---------------------------------------------------------
status, html, _ = admin_client.get('/notifications/')
record("31. Notifications Center HTTP 200", status == 200 and 'Notifications' in html, f"Status: {status}")

csrf = admin_client.get_csrf(html)
status, html, _ = admin_client.post('/notifications/mark-all-read/', {
    'csrfmiddlewaretoken': csrf
})
record("32. Notifications Mark All Read POST", status == 200, "All notifications marked read")

# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------
print("\n" + "="*60)
print("               LIVE HTTP TEST RESULTS SUMMARY")
print("="*60)
passed = sum(1 for _, p, _ in results if p)
failed = sum(1 for _, p, _ in results if not p)
total = len(results)

print(f"Total Live Checks: {total}")
print(f"Passed:            {passed}")
print(f"Failed:            {failed}")
print(f"Success Rate:      {(passed/total)*100:.1f}%")
print("="*60, flush=True)
