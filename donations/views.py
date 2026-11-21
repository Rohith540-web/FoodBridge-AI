from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from .forms import DonationForm
from .models import Donation
from ai_module.utils import predict_freshness, predict_demand_score, calculate_priority_score
from users.models import CustomUser
from notifications.models import Notification
import qrcode
from io import BytesIO


@login_required
def create_donation(request):
    if request.user.role != 'DONOR':
        return redirect('dashboard_home')

    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user

            action = request.POST.get('action')
            if action == 'draft':
                donation.status = 'DRAFT'
                donation.save()
                messages.success(request, 'Draft saved successfully.')
                return redirect('donation_history')

            donation.status = 'AVAILABLE'
            donation.save()  # Save first to get a primary key

            # AI Predictions
            donation.freshness_score = predict_freshness(donation.category, donation.preparation_time)
            donation.demand_score = predict_demand_score(donation.pickup_location)
            donation.priority_score = calculate_priority_score(donation.freshness_score, donation.demand_score)

            # Generate QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr_data = (
                f"Donation_ID:{donation.id}, Food:{donation.food_name}, "
                f"Donor_ID:{donation.donor.id}, Expiry:{donation.pickup_deadline}"
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            file_name = f"qr_{request.user.username}_{donation.id}.png"
            donation.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)

            donation.save()

            # Notify all active NGOs
            ngos = CustomUser.objects.filter(role='NGO', is_active=True)
            notifications = [
                Notification(
                    user=ngo,
                    title="New High Priority Food Available!",
                    message=(
                        f"A new donation '{donation.food_name}' is available near you "
                        f"with a priority score of {donation.priority_score}."
                    ),
                )
                for ngo in ngos
            ]
            Notification.objects.bulk_create(notifications)

            messages.success(request, 'Donation uploaded successfully.')
            return redirect('donation_history')
    else:
        form = DonationForm()
    return render(request, 'donations/create.html', {'form': form})


@login_required
def donation_history(request):
    if request.user.role == 'DONOR':
        donations = Donation.objects.filter(donor=request.user).order_by('-created_at')
    else:
        donations = Donation.objects.none()
    return render(request, 'donations/my_listings.html', {'donations': donations})


def browse_food(request):
    donations = Donation.objects.filter(status='AVAILABLE').order_by('-created_at')

    category = request.GET.get('category')
    if category:
        donations = donations.filter(category__icontains=category)

    context = {'donations': donations}
    return render(request, 'donations/browse.html', context)


def food_details(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)
    return render(request, 'donations/details.html', {'donation': donation})


def donate_food_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.role == 'DONOR':
        return redirect('create_donation')
    messages.error(request, "Only registered donors can add food.")
    return redirect('landing')


@login_required
def edit_donation(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, donor=request.user)
    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES, instance=donation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Donation updated successfully.')
            return redirect('donation_history')
    else:
        form = DonationForm(instance=donation)
    return render(request, 'donations/create.html', {'form': form, 'edit_mode': True})


@login_required
def delete_donation(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, donor=request.user)
    if request.method == 'POST':
        donation.delete()
        messages.success(request, 'Donation deleted successfully.')
    return redirect('donation_history')


@login_required
def generate_qr(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, donor=request.user)

    reservation_id = "None"
    if hasattr(donation, 'reservation'):
        reservation_id = str(donation.reservation.id)

    qr_data = (
        f"Donation_ID:{donation.id}, Food:{donation.food_name}, "
        f"Donor_ID:{donation.donor.id}, Reservation_ID:{reservation_id}, "
        f"Expiry:{donation.pickup_deadline}"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    file_name = f"qr_{request.user.username}_{donation.id}.png"

    donation.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)
    messages.success(request, 'QR Code generated successfully. You can view and download it below.')
    return redirect(f"/donations/history/?show_qr={donation.id}")


@login_required
def track_volunteer(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, donor=request.user)

    delivery = None
    if hasattr(donation, 'delivery'):
        delivery = donation.delivery

    donor_lat = donation.donor.latitude or 12.9780
    donor_lng = donation.donor.longitude or 77.6400
    
    ngo_lat = 12.9716
    ngo_lng = 77.5946
    ngo_name = "Assigned NGO Center"
    if hasattr(donation, 'reservation') and donation.reservation.ngo:
        ngo_user = donation.reservation.ngo
        ngo_lat = ngo_user.latitude or 12.9716
        ngo_lng = ngo_user.longitude or 77.5946
        if hasattr(ngo_user, 'ngo_profile') and ngo_user.ngo_profile.organization_name:
            ngo_name = ngo_user.ngo_profile.organization_name
        else:
            ngo_name = ngo_user.username

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
    return render(request, 'donations/tracking.html', context)
