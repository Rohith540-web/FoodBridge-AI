from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.conf import settings
from .forms import CustomUserCreationForm, DonorProfileForm, NgoProfileForm, VolunteerProfileForm
from .models import DonorProfile, NgoProfile, VolunteerProfile, OTPVerification, CustomUser


def role_selection(request):
    return render(request, 'users/role_selection.html')


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        role = request.POST.get('role', 'DONOR')

        if form.is_valid():
            user = form.save(commit=False)
            user.role = role  # Apply the role from POST (form field may not capture it)
            user.is_active = False  # Require OTP verification
            user.save()

            # Create corresponding profile based on role
            if user.role == 'DONOR':
                DonorProfile.objects.create(user=user)
            elif user.role == 'NGO':
                org_name = (user.first_name + " NGO") if user.first_name else user.username
                NgoProfile.objects.create(
                    user=user,
                    organization_name=org_name,
                    registration_number="PENDING"
                )
            elif user.role == 'VOLUNTEER':
                VolunteerProfile.objects.create(user=user)

            # Generate and send OTP
            otp_code = get_random_string(length=6, allowed_chars='0123456789')
            OTPVerification.objects.update_or_create(
                user=user, defaults={'otp': otp_code}
            )

            send_mail(
                'FoodBridge AI - Account Verification',
                f'Your OTP for account verification is: {otp_code}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            request.session['verification_user_id'] = user.id
            return redirect('verify_otp')
    else:
        form = CustomUserCreationForm(initial={'role': request.GET.get('role', 'DONOR')})

    context = {
        'form': form,
        'selected_role': request.GET.get('role', 'DONOR'),
    }
    return render(request, 'users/register.html', context)


def verify_otp_view(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        return redirect('register')

    if request.method == 'POST':
        if 'cancel' in request.POST:
            try:
                user = CustomUser.objects.get(id=user_id)
                if not user.is_active:
                    user.delete()
            except CustomUser.DoesNotExist:
                pass
            request.session.pop('verification_user_id', None)
            return redirect('register')

        otp_entered = request.POST.get('otp')
        try:
            user = CustomUser.objects.get(id=user_id)
            verification = OTPVerification.objects.get(user=user)

            if verification.otp == otp_entered and verification.is_valid():
                user.is_active = True
                user.save()
                verification.delete()
                del request.session['verification_user_id']
                login(request, user)
                return redirect('dashboard_home')
            else:
                return render(request, 'users/verify_otp.html', {'error': 'Invalid or expired OTP'})
        except (CustomUser.DoesNotExist, OTPVerification.DoesNotExist):
            return render(request, 'users/verify_otp.html', {'error': 'User or OTP not found'})

    return render(request, 'users/verify_otp.html')


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_superuser or user.is_staff:
                return redirect('admin_home')
            return redirect('dashboard_home')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    # Redirect to landing on both GET and POST to avoid 500 on direct URL visits
    return redirect('landing')
