from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from donations.models import Donation
from notifications.models import Notification
from users.models import CustomUser
from volunteer.models import Delivery
from .models import Reservation

@login_required
def ngo_map_view(request):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    available_donations = Donation.objects.filter(status='AVAILABLE')
    ngo_lat = request.user.latitude or 12.9716
    ngo_lng = request.user.longitude or 77.5946
    return render(request, 'ngo/map.html', {
        'donations': available_donations,
        'ngo_lat': ngo_lat,
        'ngo_lng': ngo_lng
    })

@login_required
def reserve_donation(request, donation_id):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    donation = get_object_or_404(Donation, id=donation_id, status='AVAILABLE')
    
    if request.method == 'POST':
        from volunteer.models import Delivery
        from users.models import CustomUser
        from notifications.models import Notification
        
        Reservation.objects.create(ngo=request.user, donation=donation)
        donation.status = 'RESERVED'  # Fixed: was invalid 'ASSIGNED'
        donation.save()
        
        # Auto-assign a random volunteer
        volunteer = CustomUser.objects.filter(role='VOLUNTEER', is_active=True).first()
        if volunteer:
            Delivery.objects.create(volunteer=volunteer, donation=donation, status='ASSIGNED')
            
        # Notify the donor
        Notification.objects.create(
            user=donation.donor,
            title="Food Reserved!",
            message=f"Your donation '{donation.food_name}' has been reserved by {request.user.username}. A volunteer has been assigned to pick it up."
        )
        
        from django.contrib import messages
        messages.success(request, f"Successfully reserved '{donation.food_name}'. A volunteer is on the way.")
        return redirect('ngo_reservations')
        
    return redirect('ngo_map_view')

@login_required
def cancel_reservation(request, reservation_id):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    reservation = get_object_or_404(Reservation, id=reservation_id, ngo=request.user)
    donation = reservation.donation
    
    # Only allow cancellation before the food has been physically picked up or delivered
    if donation.status in ['PICKED_UP', 'DELIVERED']:
        messages.error(request, "Cannot cancel this reservation because food pickup or delivery is already in progress.")
        return redirect('ngo_reservations')
        
    if request.method == 'POST':
        # If there is an associated delivery, notify volunteer and remove delivery
        if hasattr(donation, 'delivery'):
            vol = donation.delivery.volunteer
            if vol:
                Notification.objects.create(
                    user=vol,
                    title="Delivery Assignment Cancelled",
                    message=f"The NGO {request.user.username} cancelled the reservation for '{donation.food_name}'."
                )
            donation.delivery.delete()
            
        # Revert donation status to AVAILABLE
        donation.status = 'AVAILABLE'
        donation.save()
        
        # Notify donor
        Notification.objects.create(
            user=donation.donor,
            title="Reservation Cancelled",
            message=f"The NGO {request.user.username} cancelled their reservation for '{donation.food_name}'. Your donation is now AVAILABLE again."
        )
        
        food_name = donation.food_name
        reservation.delete()
        messages.success(request, f"Reservation for '{food_name}' was cancelled successfully. The food is now available for other NGOs.")
        
    return redirect('ngo_reservations')


@login_required
def my_reservations(request):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    reservations = Reservation.objects.filter(ngo=request.user).order_by('-reserved_at')
    return render(request, 'ngo/reservations.html', {'reservations': reservations})

@login_required
def confirm_pickup(request, donation_id):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    donation = get_object_or_404(Donation, id=donation_id)
    # Verify this NGO actually reserved it
    reservation = get_object_or_404(Reservation, donation=donation, ngo=request.user)
    
    if request.method == 'POST':
        donation.status = 'DELIVERED'
        donation.save()
        
        if hasattr(donation, 'delivery'):
            from django.utils import timezone
            donation.delivery.status = 'DELIVERED'
            donation.delivery.delivered_at = timezone.now()
            donation.delivery.save()
            
        return redirect('ngo_reservations')
        
    return redirect('ngo_reservations')

@login_required
def ngo_track_volunteer(request, donation_id):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    donation = get_object_or_404(Donation, id=donation_id)
    reservation = get_object_or_404(Reservation, donation=donation, ngo=request.user)
    
    delivery = None
    if hasattr(donation, 'delivery'):
        delivery = donation.delivery
        
    donor_lat = donation.donor.latitude or 12.9780
    donor_lng = donation.donor.longitude or 77.6400
    
    ngo_lat = request.user.latitude or 12.9716
    ngo_lng = request.user.longitude or 77.5946
    ngo_name = "Your NGO Center"
    if hasattr(request.user, 'ngo_profile') and request.user.ngo_profile.organization_name:
        ngo_name = request.user.ngo_profile.organization_name

    vol_lat = 12.9352
    vol_lng = 77.6245
    vol_name = "Volunteer"
    if delivery and delivery.volunteer:
        vol_lat = delivery.volunteer.latitude or 12.9352
        vol_lng = delivery.volunteer.longitude or 77.6245
        vol_name = delivery.volunteer.username

    google_maps_url = f"https://www.google.com/maps/dir/?api=1&origin={donor_lat},{donor_lng}&destination={ngo_lat},{ngo_lng}&travelmode=driving"

    context = {
        'donation': donation,
        'delivery': delivery,
        'reservation': reservation,
        'donor_lat': donor_lat,
        'donor_lng': donor_lng,
        'ngo_lat': ngo_lat,
        'ngo_lng': ngo_lng,
        'ngo_name': ngo_name,
        'vol_lat': vol_lat,
        'vol_lng': vol_lng,
        'vol_name': vol_name,
        'google_maps_url': google_maps_url,
    }
    return render(request, 'ngo/tracking.html', context)

@login_required
def qr_scanner(request, donation_id):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    donation = get_object_or_404(Donation, id=donation_id)
    reservation = get_object_or_404(Reservation, donation=donation, ngo=request.user)
    
    if request.method == 'POST':
        scanned_data = request.POST.get('qr_code_data', '').strip()
        if scanned_data and scanned_data != 'simulated':
            expected_token = f"Donation_ID:{donation.id}"
            if expected_token not in scanned_data and str(donation.id) not in scanned_data:
                from django.contrib import messages
                messages.error(request, f"Scanned QR Code does not match donation #{donation.id} ({donation.food_name}). Please scan the correct QR code.")
                return redirect('ngo_qr_scanner', donation_id=donation.id)

        donation.status = 'PICKED_UP'
        donation.save()
        
        if hasattr(donation, 'delivery'):
            donation.delivery.status = 'DELIVERED'
            from django.utils import timezone
            donation.delivery.delivered_at = timezone.now()
            donation.delivery.save()
            
        from django.contrib import messages
        messages.success(request, f"QR Verification Successful! Food '{donation.food_name}' marked as received.")
        return redirect('ngo_reservations')
        
    return render(request, 'ngo/qr_scanner.html', {'donation': donation})
