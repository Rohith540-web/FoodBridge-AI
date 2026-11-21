import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodbridge_project.settings')
django.setup()

from users.models import CustomUser, DonorProfile, NgoProfile, VolunteerProfile

def create_demo_users():

    # ── ADMIN ──────────────────────────────────────────────────────────────
    if not CustomUser.objects.filter(username='admin').exists():
        CustomUser.objects.create_superuser(
            username='admin',
            email='admin@foodbridge.ai',
            password='Pass@1234',
            first_name='Super',
            last_name='Admin',
        )
        print("✅ Created superuser: admin")
    else:
        u = CustomUser.objects.get(username='admin')
        u.set_password('Pass@1234')
        u.is_active = True
        u.save()
        print("🔄 Reset admin password")

    # ── DONOR ──────────────────────────────────────────────────────────────
    if not CustomUser.objects.filter(username='donor_demo').exists():
        donor = CustomUser.objects.create_user(
            username='donor_demo',
            email='donor@foodbridge.ai',
            password='Pass@1234',
            role='DONOR',
            first_name='Ravi',
            last_name='Kumar',
            phone_number='9876543001',
            address='123 MG Road, Bengaluru',
            is_active=True,
        )
        DonorProfile.objects.create(
            user=donor,
            donor_type='Restaurant',
            organization_name='Ravi Kitchen',
            contact_details='ravi@ravikitchen.com | 9876543001',
            food_safety_license='FSL-2024-BLR-001',
            is_verified=True,
        )
        print("✅ Created DONOR: donor_demo")
    else:
        u = CustomUser.objects.get(username='donor_demo')
        u.set_password('Pass@1234')
        u.is_active = True
        u.save()
        print("🔄 Reset donor_demo password")

    # ── NGO ────────────────────────────────────────────────────────────────
    if not CustomUser.objects.filter(username='ngo_demo').exists():
        ngo = CustomUser.objects.create_user(
            username='ngo_demo',
            email='ngo@foodbridge.ai',
            password='Pass@1234',
            role='NGO',
            first_name='Priya',
            last_name='Sharma',
            phone_number='9876543002',
            address='45 Shelter Lane, Bengaluru',
            latitude=12.9716,
            longitude=77.5946,
            is_active=True,
        )
        NgoProfile.objects.create(
            user=ngo,
            organization_name='Hope Foundation',
            registration_number='NGO-KA-2024-0042',
            service_area='Bengaluru Central',
            contact_person='Priya Sharma',
            organization_description='Serving underprivileged communities since 2010.',
            capacity='200',
            is_verified=True,
        )
        print("✅ Created NGO: ngo_demo")
    else:
        u = CustomUser.objects.get(username='ngo_demo')
        u.set_password('Pass@1234')
        u.is_active = True
        u.save()
        print("🔄 Reset ngo_demo password")

    # ── VOLUNTEER ──────────────────────────────────────────────────────────
    if not CustomUser.objects.filter(username='volunteer_demo').exists():
        vol = CustomUser.objects.create_user(
            username='volunteer_demo',
            email='volunteer@foodbridge.ai',
            password='Pass@1234',
            role='VOLUNTEER',
            first_name='Arjun',
            last_name='Mehta',
            phone_number='9876543003',
            address='78 Green Park, Bengaluru',
            latitude=12.9352,
            longitude=77.6245,
            is_active=True,
        )
        VolunteerProfile.objects.create(
            user=vol,
            vehicle_type='Bike',
            vehicle_details='Honda Activa - KA-01-AB-1234',
            emergency_contact='9876543099',
            availability='Mon-Sat 9AM-6PM',
            rating=4.8,
            trust_score=95,
            successful_deliveries=12,
            is_verified=True,
        )
        print("✅ Created VOLUNTEER: volunteer_demo")
    else:
        u = CustomUser.objects.get(username='volunteer_demo')
        u.set_password('Pass@1234')
        u.is_active = True
        u.save()
        print("🔄 Reset volunteer_demo password")

    print("\n" + "="*50)
    print("   DEMO LOGIN CREDENTIALS (All passwords: Pass@1234)")
    print("="*50)
    print(f"  ADMIN     → admin / Pass@1234")
    print(f"  DONOR     → donor_demo / Pass@1234")
    print(f"  NGO       → ngo_demo / Pass@1234")
    print(f"  VOLUNTEER → volunteer_demo / Pass@1234")
    print("="*50)

create_demo_users()
