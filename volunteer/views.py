from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Delivery
from donations.models import Donation
from django.utils import timezone

@login_required
def volunteer_deliveries(request):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    # Get deliveries assigned to this volunteer
    deliveries = Delivery.objects.filter(volunteer=request.user).order_by('-assigned_at')
    
    # Also fetch available reservations that don't have a delivery assigned yet
    # A volunteer could pick them up. Let's find Reservations without a Delivery.
    from ngo.models import Reservation
    pending_reservations = Reservation.objects.filter(donation__delivery__isnull=True)
    
    context = {
        'deliveries': deliveries,
        'pending_reservations': pending_reservations
    }
    return render(request, 'volunteer/deliveries.html', context)

@login_required
def accept_delivery(request, reservation_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    from ngo.models import Reservation
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Create delivery
    # Use get_or_create to prevent race-condition duplicate deliveries
    Delivery.objects.get_or_create(
        donation=reservation.donation,
        defaults={'volunteer': request.user, 'status': 'ASSIGNED'}
    )
    
    return redirect('volunteer_deliveries')

@login_required
def navigation(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user)
    donation = delivery.donation

    donor_lat = donation.donor.latitude or 12.9780
    donor_lng = donation.donor.longitude or 77.6400

    ngo_lat = 12.9716
    ngo_lng = 77.5946
    ngo_name = "NGO Center"
    if hasattr(donation, 'reservation') and donation.reservation.ngo:
        ngo_user = donation.reservation.ngo
        ngo_lat = ngo_user.latitude or 12.9716
        ngo_lng = ngo_user.longitude or 77.5946
        if hasattr(ngo_user, 'ngo_profile') and ngo_user.ngo_profile.organization_name:
            ngo_name = ngo_user.ngo_profile.organization_name
        else:
            ngo_name = ngo_user.username

    vol_lat = request.user.latitude or 12.9352
    vol_lng = request.user.longitude or 77.6245

    # If delivery is ASSIGNED (heading to donor), direct to donor. If IN_TRANSIT, direct to NGO.
    if delivery.status == 'ASSIGNED':
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&origin={vol_lat},{vol_lng}&destination={donor_lat},{donor_lng}&travelmode=driving"
    else:
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&origin={donor_lat},{donor_lng}&destination={ngo_lat},{ngo_lng}&travelmode=driving"

    context = {
        'delivery': delivery,
        'donation': donation,
        'donor_lat': donor_lat,
        'donor_lng': donor_lng,
        'ngo_lat': ngo_lat,
        'ngo_lng': ngo_lng,
        'ngo_name': ngo_name,
        'vol_lat': vol_lat,
        'vol_lng': vol_lng,
        'google_maps_url': google_maps_url,
    }
    return render(request, 'volunteer/navigation.html', context)

@login_required
def pickup_qr_scanner(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user)
    
    if request.method == 'POST':
        delivery.status = 'IN_TRANSIT'
        delivery.picked_up_at = timezone.now()
        delivery.save()
        
        delivery.donation.status = 'PICKED_UP'
        delivery.donation.save()
        
        from notifications.models import Notification
        Notification.objects.create(
            user=delivery.donation.donor,
            title="Food Picked Up!",
            message=f"Your donation '{delivery.donation.food_name}' was picked up by volunteer {request.user.username}."
        )
        if hasattr(delivery.donation, 'reservation'):
            Notification.objects.create(
                user=delivery.donation.reservation.ngo,
                title="Food is on the way!",
                message=f"The donation '{delivery.donation.food_name}' is in transit to your location."
            )
            
        from django.contrib import messages
        messages.success(request, 'Pickup verified successfully! Status updated to In Transit.')
        return redirect('volunteer_deliveries')
        
    return render(request, 'volunteer/qr_scanner.html', {'delivery': delivery, 'scan_type': 'pickup'})

@login_required
def delivery_qr_scanner(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user)
    
    if request.method == 'POST':
        delivery.status = 'DELIVERED'
        delivery.delivered_at = timezone.now()
        delivery.save()
        
        delivery.donation.status = 'DELIVERED'
        delivery.donation.save()
        
        from django.contrib import messages
        messages.success(request, 'Delivery verified successfully! Reward Points earned.')
        return redirect('delivery_success', delivery_id=delivery.id)
        
    return render(request, 'volunteer/qr_scanner.html', {'delivery': delivery, 'scan_type': 'delivery'})

@login_required
def delivery_success(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user, status='DELIVERED')
    return render(request, 'volunteer/certificate.html', {'delivery': delivery})
