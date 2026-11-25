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
    ngo_lat = request.user.latitude or 13.0827
    ngo_lng = request.user.longitude or 80.2707
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
        
        # Check if NGO directly assigned a specific volunteer
        chosen_vol_id = request.POST.get('volunteer_id')
        if chosen_vol_id:
            chosen_vol = CustomUser.objects.filter(id=chosen_vol_id, role='VOLUNTEER', is_active=True).first()
            if chosen_vol:
                Delivery.objects.create(volunteer=chosen_vol, donation=donation, status='ASSIGNED')
                Notification.objects.create(
                    user=chosen_vol,
                    title="New Delivery Assigned!",
                    message=f"NGO {request.user.username} has directly assigned you to deliver '{donation.food_name}'."
                )
            
        # Notify the donor
        Notification.objects.create(
            user=donation.donor,
            title="Food Reserved!",
            message=f"Your donation '{donation.food_name}' has been reserved by {request.user.username}. Waiting for a volunteer to choose and accept pickup."
        )

        # Notify active volunteers that a new rescue task is available to claim
        active_volunteers = CustomUser.objects.filter(role='VOLUNTEER', is_active=True)
        for vol in active_volunteers:
            Notification.objects.create(
                user=vol,
                title="New Food Rescue Available!",
                message=f"'{donation.food_name}' ({donation.quantity}) at {donation.pickup_location[:35]} is available for pickup. Claim this delivery now!"
            )
            
        from django.contrib import messages
        messages.success(request, f"Successfully reserved '{donation.food_name}'. It is now open on the Volunteer Rescue Board for volunteers to choose!")
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
def assign_volunteer(request, reservation_id):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    from users.models import CustomUser
    from volunteer.models import Delivery
    from notifications.models import Notification
    
    reservation = get_object_or_404(Reservation, id=reservation_id, ngo=request.user)
    if request.method == 'POST':
        volunteer_id = request.POST.get('volunteer_id')
        if volunteer_id == 'unassign' or not volunteer_id:
            # Release back to open pool
            if hasattr(reservation.donation, 'delivery'):
                old_vol = reservation.donation.delivery.volunteer
                reservation.donation.delivery.delete()
                if old_vol:
                    Notification.objects.create(
                        user=old_vol,
                        title="Delivery Assignment Released",
                        message=f"The delivery task for '{reservation.donation.food_name}' was released back to the open volunteer board."
                    )
            messages.success(request, f"'{reservation.donation.food_name}' is now open on the Volunteer Rescue Board for any volunteer to choose.")
        else:
            vol = get_object_or_404(CustomUser, id=volunteer_id, role='VOLUNTEER', is_active=True)
            delivery, created = Delivery.objects.get_or_create(
                donation=reservation.donation,
                defaults={'volunteer': vol, 'status': 'ASSIGNED'}
            )
            if not created:
                delivery.volunteer = vol
                delivery.status = 'ASSIGNED'
                delivery.save()
                
            Notification.objects.create(
                user=vol,
                title="Delivery Assigned by NGO",
                message=f"NGO {request.user.username} has assigned you to deliver '{reservation.donation.food_name}'."
            )
            messages.success(request, f"Assigned volunteer '{vol.username}' to deliver '{reservation.donation.food_name}'.")
    return redirect('ngo_reservations')

@login_required
def my_reservations(request):
    if request.user.role != 'NGO':
        return redirect('dashboard_home')
        
    from users.models import CustomUser
    reservations = Reservation.objects.filter(ngo=request.user).order_by('-reserved_at')
    active_volunteers = CustomUser.objects.filter(role='VOLUNTEER', is_active=True).exclude(username='volunteer_demo')
    return render(request, 'ngo/reservations.html', {
        'reservations': reservations,
        'active_volunteers': active_volunteers
    })

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
        
    donor_lat = donation.get_latitude
    donor_lng = donation.get_longitude
    
    ngo_lat = request.user.latitude or 13.0827
    ngo_lng = request.user.longitude or 80.2707
    ngo_name = "Your NGO Center"
    if hasattr(request.user, 'ngo_profile') and request.user.ngo_profile.organization_name:
        ngo_name = request.user.ngo_profile.organization_name
    else:
        ngo_name = request.user.username

    vol_lat = 13.0280
    vol_lng = 80.0163
    vol_name = "Volunteer"
    if delivery and delivery.volunteer:
        vol_lat = delivery.volunteer.latitude or 13.0280
        vol_lng = delivery.volunteer.longitude or 80.0163
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
