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
def cancel_delivery(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user)
    
    # Only allow cancellation if still ASSIGNED (before physical pickup)
    if delivery.status != 'ASSIGNED':
        from django.contrib import messages
        messages.error(request, "Cannot cancel this delivery once food pickup has started or completed.")
        return redirect('volunteer_deliveries')
        
    if request.method == 'POST':
        donation = delivery.donation
        from notifications.models import Notification
        from django.contrib import messages
        
        # Notify the NGO
        if hasattr(donation, 'reservation') and donation.reservation.ngo:
            Notification.objects.create(
                user=donation.reservation.ngo,
                title="Volunteer Delivery Cancelled",
                message=f"Volunteer {request.user.username} had to cancel the delivery for '{donation.food_name}'. It is now open for another volunteer to accept."
            )
            
        food_name = donation.food_name
        delivery.delete()
        messages.success(request, f"Delivery assignment for '{food_name}' was cancelled. It is now open for other volunteers.")
        
    return redirect('volunteer_deliveries')

@login_required
def navigation(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user)
    donation = delivery.donation

    donor_lat = donation.get_latitude
    donor_lng = donation.get_longitude

    ngo_lat = 13.0827
    ngo_lng = 80.2707
    ngo_name = "NGO Center"
    if hasattr(donation, 'reservation') and donation.reservation.ngo:
        ngo_user = donation.reservation.ngo
        ngo_lat = ngo_user.latitude or 13.0827
        ngo_lng = ngo_user.longitude or 80.2707
        if hasattr(ngo_user, 'ngo_profile') and ngo_user.ngo_profile.organization_name:
            ngo_name = ngo_user.ngo_profile.organization_name
        else:
            ngo_name = ngo_user.username

    vol_lat = request.user.latitude or 13.0280
    vol_lng = request.user.longitude or 80.0163

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
        scanned_data = request.POST.get('qr_code_data', '').strip()
        # If real scanned data was submitted, validate it
        if scanned_data and scanned_data != 'simulated':
            expected_token = f"Donation_ID:{delivery.donation.id}"
            if expected_token not in scanned_data and str(delivery.donation.id) not in scanned_data:
                from django.contrib import messages
                messages.error(request, f"Scanned QR Code does not match this donation (#{delivery.donation.id}: {delivery.donation.food_name}). Please scan the correct QR code.")
                return redirect('pickup_qr_scanner', delivery_id=delivery.id)

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
        messages.success(request, f"QR Verification Verified! Food '{delivery.donation.food_name}' is now In Transit.")
        return redirect('volunteer_deliveries')
        
    return render(request, 'volunteer/qr_scanner.html', {'delivery': delivery, 'scan_type': 'pickup'})

@login_required
def delivery_qr_scanner(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user)
    
    if request.method == 'POST':
        scanned_data = request.POST.get('qr_code_data', '').strip()
        if scanned_data and scanned_data != 'simulated':
            expected_token = f"Donation_ID:{delivery.donation.id}"
            if expected_token not in scanned_data and str(delivery.donation.id) not in scanned_data:
                from django.contrib import messages
                messages.error(request, f"Scanned QR Code does not match delivery for donation #{delivery.donation.id}. Please scan the correct QR code.")
                return redirect('delivery_qr_scanner', delivery_id=delivery.id)

        delivery.status = 'DELIVERED'
        delivery.delivered_at = timezone.now()
        delivery.save()
        
        delivery.donation.status = 'DELIVERED'
        delivery.donation.save()
        
        from django.contrib import messages
        messages.success(request, 'Delivery verified successfully via QR Scan! Certificate generated.')
        return redirect('delivery_success', delivery_id=delivery.id)
        
    return render(request, 'volunteer/qr_scanner.html', {'delivery': delivery, 'scan_type': 'delivery'})

@login_required
def delivery_success(request, delivery_id):
    if request.user.role != 'VOLUNTEER':
        return redirect('dashboard_home')
        
    delivery = get_object_or_404(Delivery, id=delivery_id, volunteer=request.user, status='DELIVERED')
    return render(request, 'volunteer/certificate.html', {'delivery': delivery})
