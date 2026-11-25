import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodbridge_project.settings')
django.setup()

from django.test import Client
from users.models import CustomUser, DonorProfile, NgoProfile, VolunteerProfile, OTPVerification
from donations.models import Donation
from ngo.models import Reservation
from volunteer.models import Delivery
from notifications.models import Notification

results = []

def record(test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((test_name, status, detail))
    icon = "[PASS]" if passed else "[FAIL]"
    print(f"{icon} {test_name}: {detail}", flush=True)

print("==================================================")
print("   FOODBRIDGE AI - COMPREHENSIVE FEATURE TEST     ")
print("==================================================")

client = Client()

# ---------------------------------------------------------------------
# 1. PUBLIC PAGES
# ---------------------------------------------------------------------
resp = client.get('/')
record("Landing Page (/) renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.get('/users/select-role/')
record("Role Selection Page renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.get('/donations/browse/')
record("Browse Food Page renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.get('/donations/browse/?category=grains')
record("Browse Food with Category Filter renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.get('/users/login/')
record("Login Page renders", resp.status_code == 200, f"Status: {resp.status_code}")

# ---------------------------------------------------------------------
# 2. REGISTRATION & OTP VERIFICATION FLOW
# ---------------------------------------------------------------------
test_reg_email = "test_reg_donor@foodbridge.ai"
CustomUser.objects.filter(email=test_reg_email).delete()

resp = client.post('/users/register/', {
    'username': 'new_reg_donor',
    'email': test_reg_email,
    'password1': 'StrongPass123!',
    'password2': 'StrongPass123!',
    'role': 'DONOR',
    'phone_number': '9988776655',
    'address': '100 Test St, City',
})
record("Registration POST redirects to OTP", resp.status_code == 302 and resp.url == '/users/verify-otp/', f"Redirected to: {resp.url if resp.status_code == 302 else resp.status_code}")

# Check user created with inactive status
user = CustomUser.objects.filter(email=test_reg_email).first()
record("New User created with role DONOR and inactive", user is not None and user.role == 'DONOR' and not user.is_active, f"Role: {user.role if user else 'None'}, Active: {user.is_active if user else 'None'}")

# Verify OTP
otp_obj = OTPVerification.objects.filter(user=user).first()
record("OTP generated for new user", otp_obj is not None, f"OTP: {otp_obj.otp if otp_obj else 'None'}")

if otp_obj:
    resp = client.post('/users/verify-otp/', {'otp': otp_obj.otp})
    user.refresh_from_db()
    record("OTP Verification activates user & logs in", resp.status_code == 302 and user.is_active, f"User active: {user.is_active}, Redirect: {resp.url if resp.status_code == 302 else resp.status_code}")

client.logout()

# ---------------------------------------------------------------------
# 3. DONOR FLOW
# ---------------------------------------------------------------------
donor = CustomUser.objects.get(username='donor_demo')
login_ok = client.login(username='donor_demo', password='Pass@1234')
record("Donor Login", login_ok, "Logged in as donor_demo")

resp = client.get('/dashboard/')
record("Donor Dashboard renders", resp.status_code == 200 and b'Dashboard' in resp.content, f"Status: {resp.status_code}")

# Create Donation
now = timezone.now()
prep_time = (now - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
pickup_time = (now + timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M')

resp = client.post('/donations/create/', {
    'food_name': 'Automated Fresh Meals',
    'category': 'cooked meals',
    'quantity': '25 meals',
    'preparation_time': prep_time,
    'pickup_deadline': pickup_time,
    'pickup_location': '77 Tech Park, Shelter Zone, Bengaluru',
    'storage_type': 'Insulated Warmer',
    'special_instructions': 'Handle carefully',
    'description': 'Freshly prepared vegetarian meals',
    'action': 'submit'
})
record("Donation Create POST succeeds", resp.status_code == 302, f"Redirected to: {resp.url if resp.status_code == 302 else resp.status_code}")

donation = Donation.objects.filter(food_name='Automated Fresh Meals', donor=donor).order_by('-created_at').first()
record("Donation exists with status AVAILABLE", donation is not None and donation.status == 'AVAILABLE', f"Status: {donation.status if donation else 'None'}")

if donation:
    record("AI Freshness Score computed", donation.freshness_score is not None and 0.0 <= donation.freshness_score <= 1.0, f"Score: {donation.freshness_score}")
    record("AI Demand Score computed", donation.demand_score is not None and 0.0 <= donation.demand_score <= 1.0, f"Score: {donation.demand_score}")
    record("AI Priority Score computed", donation.priority_score is not None and 0.0 <= donation.priority_score <= 100.0, f"Score: {donation.priority_score}")
    record("Donation QR Code generated", bool(donation.qr_code), f"QR File: {donation.qr_code.name if donation.qr_code else 'None'}")

# Check NGO Notification created
ngo_notif = Notification.objects.filter(title__icontains="New High Priority Food Available").order_by('-created_at').first()
record("NGO Notification triggered on donation", ngo_notif is not None, f"Notification: {ngo_notif.title if ngo_notif else 'None'}")

# View My Listings
resp = client.get('/donations/history/')
record("Donor My Listings renders", resp.status_code == 200, f"Status: {resp.status_code}")

# View Food Details
resp = client.get(f'/donations/details/{donation.id}/')
record("Food Details page renders", resp.status_code == 200, f"Status: {resp.status_code}")

# Regenerate QR
resp = client.get(f'/donations/qr/{donation.id}/')
record("Regenerate QR succeeds", resp.status_code == 302, f"Redirected to: {resp.url if resp.status_code == 302 else resp.status_code}")

# Edit Donation
resp = client.post(f'/donations/edit/{donation.id}/', {
    'food_name': 'Automated Fresh Meals (Updated)',
    'category': 'cooked meals',
    'quantity': '30 meals',
    'preparation_time': prep_time,
    'pickup_deadline': pickup_time,
    'pickup_location': '77 Tech Park, Shelter Zone, Bengaluru',
    'storage_type': 'Insulated Warmer',
    'special_instructions': 'Handle carefully',
    'description': 'Updated description',
})
record("Edit Donation succeeds", resp.status_code == 302, f"Redirected to: {resp.url if resp.status_code == 302 else resp.status_code}")
donation.refresh_from_db()
record("Donation edits persisted", donation.food_name == 'Automated Fresh Meals (Updated)', f"Updated name: {donation.food_name}")

client.logout()

# ---------------------------------------------------------------------
# 4. NGO FLOW
# ---------------------------------------------------------------------
ngo = CustomUser.objects.get(username='ngo_demo')
login_ok = client.login(username='ngo_demo', password='Pass@1234')
record("NGO Login", login_ok, "Logged in as ngo_demo")

resp = client.get('/dashboard/')
record("NGO Dashboard renders", resp.status_code == 200 and b'Dashboard' in resp.content, f"Status: {resp.status_code}")

resp = client.get('/ngo/map/')
record("NGO Map view renders", resp.status_code == 200, f"Status: {resp.status_code}")

# Reserve the donation
resp = client.post(f'/ngo/reserve/{donation.id}/')
record("NGO Reserve Donation succeeds", resp.status_code == 302, f"Redirect: {resp.url if resp.status_code == 302 else resp.status_code}")

donation.refresh_from_db()
record("Donation status changed to RESERVED", donation.status == 'RESERVED', f"Status: {donation.status}")

reservation = Reservation.objects.filter(donation=donation, ngo=ngo).first()
record("Reservation created in DB", reservation is not None, f"Reservation ID: {reservation.id if reservation else 'None'}")

# Check donation is open for volunteer choice on rescue board
delivery_before = Delivery.objects.filter(donation=donation).first()
record("Donation open on Volunteer Rescue Board", delivery_before is None, "Waiting for volunteer to choose")

# Check donor notification
donor_notif = Notification.objects.filter(user=donor, title="Food Reserved!").order_by('-created_at').first()
record("Donor received Food Reserved notification", donor_notif is not None, f"Notif: {donor_notif.title if donor_notif else 'None'}")

# NGO Reservations page
resp = client.get('/ngo/reservations/')
record("NGO Reservations page renders", resp.status_code == 200, f"Status: {resp.status_code}")

# NGO Track Volunteer page
resp = client.get(f'/ngo/track/{donation.id}/')
record("NGO Track Volunteer page renders", resp.status_code == 200, f"Status: {resp.status_code}")

client.logout()

# ---------------------------------------------------------------------
# 5. VOLUNTEER FLOW
# ---------------------------------------------------------------------
vol = CustomUser.objects.filter(role='VOLUNTEER', is_active=True).exclude(username='volunteer_demo').first() or CustomUser.objects.filter(role='VOLUNTEER', is_active=True).first()
login_ok = client.login(username=vol.username, password='Pass@1234')
record("Volunteer Login", login_ok, f"Logged in as {vol.username}")

resp = client.get('/dashboard/')
record("Volunteer Dashboard renders", resp.status_code == 200 and b'Dashboard' in resp.content, f"Status: {resp.status_code}")

resp = client.get('/volunteer/deliveries/')
record("Volunteer Deliveries page renders", resp.status_code == 200, f"Status: {resp.status_code}")

# Volunteer chooses and accepts the reserved donation
resp = client.post(f'/volunteer/accept/{reservation.id}/')
delivery = Delivery.objects.filter(donation=donation, volunteer=vol).first()
record("Volunteer chose and claimed delivery", delivery is not None and delivery.status == 'ASSIGNED', f"Volunteer: {delivery.volunteer.username if delivery else 'None'}")

resp = client.get(f'/volunteer/navigation/{delivery.id}/')
record("Volunteer Navigation page renders", resp.status_code == 200, f"Status: {resp.status_code}")

# Pickup QR Scanner simulation
resp = client.get(f'/volunteer/scan-pickup/{delivery.id}/')
record("Volunteer Pickup QR Scanner page renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.post(f'/volunteer/scan-pickup/{delivery.id}/')
record("Volunteer Pickup QR POST succeeds", resp.status_code == 302, f"Redirect: {resp.url if resp.status_code == 302 else resp.status_code}")

delivery.refresh_from_db()
donation.refresh_from_db()
record("Delivery status updated to IN_TRANSIT", delivery.status == 'IN_TRANSIT', f"Delivery status: {delivery.status}")
record("Donation status updated to PICKED_UP", donation.status == 'PICKED_UP', f"Donation status: {donation.status}")

# Delivery QR Scanner simulation
resp = client.get(f'/volunteer/scan-delivery/{delivery.id}/')
record("Volunteer Delivery QR Scanner page renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.post(f'/volunteer/scan-delivery/{delivery.id}/')
record("Volunteer Delivery QR POST succeeds", resp.status_code == 302, f"Redirect: {resp.url if resp.status_code == 302 else resp.status_code}")

delivery.refresh_from_db()
donation.refresh_from_db()
record("Delivery status updated to DELIVERED", delivery.status == 'DELIVERED', f"Delivery status: {delivery.status}")
record("Donation status updated to DELIVERED", donation.status == 'DELIVERED', f"Donation status: {donation.status}")

# Volunteer Certificate page
resp = client.get(f'/volunteer/certificate/{delivery.id}/')
record("Volunteer Certificate renders", resp.status_code == 200, f"Status: {resp.status_code}")

# Volunteer Accept Delivery test
temp_donation = Donation.objects.create(
    donor=donor,
    food_name='Extra Food Item',
    category='bakery',
    quantity='15 bread loaves',
    preparation_time=now - timedelta(hours=1),
    pickup_deadline=now + timedelta(hours=8),
    pickup_location='Bakery Street, Bengaluru',
    storage_type='Room Temp',
    status='RESERVED'
)
temp_reservation = Reservation.objects.create(ngo=ngo, donation=temp_donation)
resp = client.post(f'/volunteer/accept/{temp_reservation.id}/')
record("Volunteer Accept Delivery POST succeeds", resp.status_code == 302, f"Redirect: {resp.url if resp.status_code == 302 else resp.status_code}")
accepted_del = Delivery.objects.filter(donation=temp_donation).first()
record("Accepted Delivery created with status ASSIGNED", accepted_del is not None and accepted_del.status == 'ASSIGNED', f"Volunteer: {accepted_del.volunteer.username if accepted_del else 'None'}")

client.logout()

# ---------------------------------------------------------------------
# 6. ADMIN FLOW
# ---------------------------------------------------------------------
admin = CustomUser.objects.get(username='admin')
login_ok = client.login(username='admin', password='Pass@1234')
record("Admin Login", login_ok, "Logged in as admin")

resp = client.get('/dashboard/admin/')
record("Admin Dashboard renders", resp.status_code == 200 and b'Admin' in resp.content, f"Status: {resp.status_code}")

resp = client.get('/dashboard/admin/users/')
record("Admin Manage Users page renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.get('/dashboard/admin/deliveries/')
record("Admin Live Deliveries page renders", resp.status_code == 200, f"Status: {resp.status_code}")

resp = client.get('/dashboard/admin/analytics/')
record("Admin AI Analytics page renders", resp.status_code == 200 and b'Analytics' in resp.content, f"Status: {resp.status_code}")

# Admin user action: suspend and approve
target_user = CustomUser.objects.filter(role='DONOR', is_superuser=False).first()
if target_user:
    resp = client.post(f'/dashboard/admin/users/{target_user.id}/suspend/')
    target_user.refresh_from_db()
    record("Admin Suspend User succeeds", not target_user.is_active, f"User active: {target_user.is_active}")

    resp = client.post(f'/dashboard/admin/users/{target_user.id}/approve/')
    target_user.refresh_from_db()
    record("Admin Approve User succeeds", target_user.is_active, f"User active: {target_user.is_active}")

client.logout()

# ---------------------------------------------------------------------
# 7. NOTIFICATIONS SYSTEM
# ---------------------------------------------------------------------
client.login(username='donor_demo', password='Pass@1234')
resp = client.get('/notifications/')
record("Notifications List renders", resp.status_code == 200, f"Status: {resp.status_code}")

notif = Notification.objects.filter(user=donor).first()
if notif:
    resp = client.get(f'/notifications/{notif.id}/read/')
    record("Notification Mark Read succeeds", resp.status_code == 302, f"Redirect: {resp.url if resp.status_code == 302 else resp.status_code}")

resp = client.post('/notifications/mark-all-read/')
record("Notification Mark All Read succeeds", resp.status_code == 302, f"Redirect: {resp.url if resp.status_code == 302 else resp.status_code}")

client.logout()

# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------
print("\n" + "="*50)
print("              TEST RESULTS SUMMARY                ")
print("==================================================")
passed_count = sum(1 for _, s, _ in results if s == "PASS")
failed_count = sum(1 for _, s, _ in results if s == "FAIL")
total = len(results)

print(f"TOTAL TESTS:  {total}")
print(f"PASSED:       {passed_count}")
print(f"FAILED:       {failed_count}")
print(f"SUCCESS RATE: {(passed_count/total)*100:.1f}%\n")

if failed_count == 0:
    print("ALL FEATURES ARE WORKING PROPERLY!")
else:
    print("FAILED TESTS:")
    for name, status, detail in results:
        if status == "FAIL":
            print(f" - {name}: {detail}")
