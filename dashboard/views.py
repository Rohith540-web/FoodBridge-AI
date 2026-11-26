from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Avg, Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from donations.models import Donation
from ngo.models import Reservation
from users.models import CustomUser
from volunteer.models import Delivery


def landing_page(request):
    featured_donations = Donation.objects.filter(status='AVAILABLE').order_by('-created_at')[:4]

    total_donations = Donation.objects.count()
    delivered_count = Donation.objects.filter(status='DELIVERED').count()
    people_fed = delivered_count * 15       # ~15 meals per donation
    co2_reduced = delivered_count * 2.5     # ~2.5 kg CO₂ per donation

    active_donors = CustomUser.objects.filter(role='DONOR', is_active=True).count()
    active_ngos = CustomUser.objects.filter(role='NGO', is_active=True).count()
    active_volunteers = CustomUser.objects.filter(role='VOLUNTEER', is_active=True).count()

    context = {
        'featured_donations': featured_donations,
        'total_donations': total_donations,
        'people_fed': people_fed,
        'co2_reduced': round(co2_reduced, 1),
        'active_donors': active_donors,
        'active_ngos': active_ngos,
        'active_volunteers': active_volunteers,
    }
    return render(request, 'landing.html', context)


@login_required
def dashboard_home(request):
    user = request.user

    if user.role == 'DONOR':
        donor_donations = Donation.objects.filter(donor=user)
        total_donations = donor_donations.count()
        pending_requests = donor_donations.filter(status='AVAILABLE').count()
        completed_donations = donor_donations.filter(status='DELIVERED').count()
        avg_score = donor_donations.exclude(freshness_score__isnull=True).aggregate(
            Avg('freshness_score')
        )['freshness_score__avg']
        recent_donations = donor_donations.order_by('-created_at')[:5]
        upcoming_pickup = donor_donations.filter(
            status__in=['RESERVED', 'ASSIGNED']
        ).order_by('pickup_deadline').first()

        context = {
            'total_donations': total_donations,
            'pending_requests': pending_requests,
            'completed_donations': completed_donations,
            'avg_ai_score': round(avg_score, 1) if avg_score else None,
            'recent_donations': recent_donations,
            'upcoming_pickup': upcoming_pickup,
        }
        return render(request, 'dashboard/donor_home.html', context)

    if user.role == 'NGO':
        ngo_reservations = Reservation.objects.filter(ngo=user)
        active_reservations = ngo_reservations.exclude(donation__status='DELIVERED').count()
        completed_rescues = ngo_reservations.filter(donation__status='DELIVERED').count()
        available_donations = Donation.objects.filter(status='AVAILABLE').count()
        impact_score = completed_rescues * 10
        recent_reservations = ngo_reservations.order_by('-reserved_at')[:5]
        incoming_delivery = ngo_reservations.exclude(
            donation__status='DELIVERED'
        ).order_by('reserved_at').first()

        context = {
            'available_donations': available_donations,
            'active_reservations': active_reservations,
            'completed_rescues': completed_rescues,
            'impact_score': impact_score,
            'recent_reservations': recent_reservations,
            'incoming_delivery': incoming_delivery,
        }
        return render(request, 'dashboard/ngo_home.html', context)

    if user.role == 'VOLUNTEER':
        volunteer_deliveries = Delivery.objects.filter(volunteer=user)
        completed_deliveries = volunteer_deliveries.filter(status='DELIVERED').count()
        active_deliveries = volunteer_deliveries.exclude(status='DELIVERED').count()
        reward_points = completed_deliveries * 50
        trust_score = min(100, 80 + completed_deliveries * 2)
        current_delivery = volunteer_deliveries.exclude(
            status='DELIVERED'
        ).order_by('assigned_at').first()

        context = {
            'completed_deliveries': completed_deliveries,
            'active_deliveries': active_deliveries,
            'reward_points': reward_points,
            'trust_score': trust_score,
            'current_delivery': current_delivery,
        }
        return render(request, 'dashboard/volunteer_home.html', context)

    # Fallback for Admin role logged in without is_staff
    total_donations = Donation.objects.count()
    delivered_count = Donation.objects.filter(status='DELIVERED').count()
    context = {
        'total_donations': total_donations,
        'people_fed': delivered_count * 15,
        'co2_reduced': round(delivered_count * 2.5, 1),
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def admin_home(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('dashboard_home')

    total_users = CustomUser.objects.count()
    live_deliveries = Delivery.objects.filter(status__in=['ASSIGNED', 'IN_TRANSIT']).count()
    total_rescues = Delivery.objects.filter(status='DELIVERED').count()

    # Calculate real AI efficiency: percentage of donations that got a freshness score
    total_scored = Donation.objects.exclude(freshness_score__isnull=True).count()
    total_all = Donation.objects.count()
    ai_efficiency = round((total_scored / total_all * 100), 1) if total_all else 0.0

    context = {
        'total_users': total_users,
        'live_deliveries': live_deliveries,
        'total_rescues': total_rescues,
        'ai_efficiency': ai_efficiency,
    }
    return render(request, 'dashboard/admin_home.html', context)


@login_required
def admin_users(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('dashboard_home')

    users = CustomUser.objects.exclude(is_superuser=True).select_related(
        'donor_profile', 'ngo_profile', 'volunteer_profile'
    ).order_by('-date_joined')
    donors = users.filter(role='DONOR')
    ngos = users.filter(role='NGO')
    volunteers = users.filter(role='VOLUNTEER')

    import json
    users_map_data = []
    for u in users:
        lat = u.latitude
        lng = u.longitude
        if not lat or not lng:
            addr = (u.address or '').lower()
            if 'thiruvallur' in addr or 'tiruvallur' in addr:
                lat, lng = 13.1433, 79.9079
            elif 'saveetha' in addr or 'thandalam' in addr:
                lat, lng = 13.0280, 80.0163
            elif 'sriperumbudur' in addr:
                lat, lng = 12.9675, 79.9439
            elif 'mannur' in addr:
                lat, lng = 13.0199, 79.9880
            elif 'chennai' in addr or 'madras' in addr or 'mgr nagar' in addr:
                lat, lng = 13.0827, 80.2707
            else:
                if u.role == 'DONOR':
                    lat, lng = 13.0827, 80.2707
                elif u.role == 'NGO':
                    lat, lng = 13.0500, 80.2300
                elif u.role == 'VOLUNTEER':
                    lat, lng = 13.0289, 80.0191
                else:
                    lat, lng = 13.0827, 80.2707

        details = ""
        org_name = ""
        if u.role == 'DONOR' and hasattr(u, 'donor_profile'):
            org_name = u.donor_profile.organization_name or u.username
            details = f"Org: {org_name} | Type: {u.donor_profile.donor_type} | FSL: {u.donor_profile.food_safety_license or 'Verified'}"
        elif u.role == 'NGO' and hasattr(u, 'ngo_profile'):
            org_name = u.ngo_profile.organization_name or u.username
            details = f"Org: {org_name} | Reg: {u.ngo_profile.registration_number or 'N/A'} | Area: {u.ngo_profile.service_area or 'General'}"
        elif u.role == 'VOLUNTEER' and hasattr(u, 'volunteer_profile'):
            details = f"Vehicle: {u.volunteer_profile.vehicle_type or 'Bike'} | Trust: {u.volunteer_profile.trust_score}% | Deliveries: {u.volunteer_profile.successful_deliveries}"

        users_map_data.append({
            'id': u.id,
            'username': u.username,
            'org_name': org_name,
            'email': u.email,
            'phone': u.phone_number or 'Not provided',
            'role': u.role,
            'address': u.address or 'Address not specified',
            'lat': float(lat),
            'lng': float(lng),
            'is_active': u.is_active,
            'details': details,
            'date_joined': u.date_joined.strftime('%b %d, %Y'),
        })

    context = {
        'donors': donors,
        'ngos': ngos,
        'volunteers': volunteers,
        'users_map_json': json.dumps(users_map_data),
    }
    return render(request, 'dashboard/admin_users.html', context)


@login_required
def admin_user_action(request, user_id, action):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('dashboard_home')

    target_user = get_object_or_404(CustomUser, id=user_id)

    if action == 'approve':
        target_user.is_active = True
        target_user.save()
        messages.success(request, f"User {target_user.username} approved.")
    elif action == 'suspend':
        target_user.is_active = False
        target_user.save()
        messages.warning(request, f"User {target_user.username} suspended.")
    elif action == 'delete':
        if request.method == 'POST':
            username = target_user.username
            target_user.delete()
            messages.error(request, f"User {username} deleted.")
        else:
            messages.error(request, "Delete requires POST.")

    return redirect('admin_users')


@login_required
def admin_deliveries(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('dashboard_home')

    active_deliveries = Delivery.objects.filter(
        status__in=['ASSIGNED', 'IN_TRANSIT']
    ).select_related(
        'volunteer', 'volunteer__volunteer_profile',
        'donation', 'donation__donor', 'donation__donor__donor_profile',
        'donation__reservation', 'donation__reservation__ngo', 'donation__reservation__ngo__ngo_profile'
    ).order_by('-assigned_at')

    completed_deliveries = Delivery.objects.filter(
        status='DELIVERED'
    ).select_related(
        'volunteer',
        'donation', 'donation__donor',
        'donation__reservation', 'donation__reservation__ngo'
    ).order_by('-delivered_at')

    import json
    tracking_data = []
    for d in active_deliveries:
        vol_lat = d.volunteer.latitude if d.volunteer and d.volunteer.latitude else 13.0289
        vol_lng = d.volunteer.longitude if d.volunteer and d.volunteer.longitude else 80.0191

        donor_lat = d.donation.get_latitude
        donor_lng = d.donation.get_longitude

        ngo_user = getattr(getattr(d.donation, 'reservation', None), 'ngo', None)
        ngo_lat = (ngo_user.latitude if ngo_user and ngo_user.latitude else 13.0500)
        ngo_lng = (ngo_user.longitude if ngo_user and ngo_user.longitude else 80.2300)

        vol_profile = getattr(d.volunteer, 'volunteer_profile', None)
        donor_profile = getattr(d.donation.donor, 'donor_profile', None)
        ngo_profile = getattr(ngo_user, 'ngo_profile', None) if ngo_user else None

        tracking_data.append({
            'delivery_id': d.id,
            'food_name': d.donation.food_name,
            'quantity': d.donation.quantity,
            'status': d.status,
            'status_display': d.get_status_display(),
            'assigned_at': d.assigned_at.strftime('%b %d, %H:%M') if d.assigned_at else 'Recent',
            'volunteer': {
                'username': d.volunteer.username,
                'phone': d.volunteer.phone_number or 'N/A',
                'lat': float(vol_lat),
                'lng': float(vol_lng),
                'vehicle': getattr(vol_profile, 'vehicle_type', 'Bike') or 'Bike',
                'trust_score': getattr(vol_profile, 'trust_score', 100),
            },
            'donor': {
                'username': d.donation.donor.username,
                'org': getattr(donor_profile, 'organization_name', '') or d.donation.donor.username,
                'pickup_location': d.donation.pickup_location or 'Pickup Address',
                'phone': d.donation.donor.phone_number or 'N/A',
                'lat': float(donor_lat),
                'lng': float(donor_lng),
            },
            'ngo': {
                'username': ngo_user.username if ngo_user else 'NGO Center',
                'org': getattr(ngo_profile, 'organization_name', '') if ngo_profile else (ngo_user.username if ngo_user else 'NGO Center'),
                'address': ngo_user.address if ngo_user and ngo_user.address else 'NGO Dropoff Center',
                'phone': ngo_user.phone_number if ngo_user and ngo_user.phone_number else 'N/A',
                'lat': float(ngo_lat),
                'lng': float(ngo_lng),
            }
        })

    context = {
        'deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
        'tracking_json': json.dumps(tracking_data),
    }
    return render(request, 'dashboard/admin_deliveries.html', context)


@login_required
def admin_analytics(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('dashboard_home')

    delivered_count = Donation.objects.filter(status='DELIVERED').count()
    meals_served = delivered_count * 15
    waste_reduced = delivered_count * 5     # kg
    co2_savings = delivered_count * 2.5     # kg

    # Average time from donation creation to pickup (in minutes)
    delivered = Donation.objects.filter(status='DELIVERED').select_related('delivery')
    total_time_mins = 0
    count = 0
    for d in delivered:
        if hasattr(d, 'delivery') and d.delivery.picked_up_at:
            diff = (d.delivery.picked_up_at - d.created_at).total_seconds() / 60
            if diff > 0:
                total_time_mins += diff
                count += 1

    avg_pickup_time = round(total_time_mins / count) if count > 0 else 45

    # Real AI accuracy: % of donations that received a freshness prediction
    total_all = Donation.objects.count()
    total_scored = Donation.objects.exclude(freshness_score__isnull=True).count()
    ai_accuracy = round((total_scored / total_all * 100), 1) if total_all else 0.0

    context = {
        'meals_served': meals_served,
        'waste_reduced': waste_reduced,
        'co2_savings': round(co2_savings, 1),
        'avg_pickup_time': avg_pickup_time,
        'ai_accuracy': ai_accuracy,
    }
    return render(request, 'dashboard/admin_analytics.html', context)
