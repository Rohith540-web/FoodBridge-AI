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
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            phone = form.cleaned_data.get('phone_number')

            # Clean up any stale unverified (is_active=False) registrations with matching username, email, or phone
            from django.db.models import Q
            stale_query = Q(username=username) | Q(email__iexact=email)
            if phone:
                stale_query |= Q(phone_number=phone)
            CustomUser.objects.filter(is_active=False).filter(stale_query).delete()

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

            try:
                send_mail(
                    'FoodBridge AI - Account Verification Code',
                    f'Welcome to FoodBridge AI!\n\nYour 6-digit OTP verification code is: {otp_code}\n\nThis code is valid for 10 minutes.\n\nThank you,\nFoodBridge AI Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"[EMAIL WARNING] Could not dispatch email via SMTP: {e}")

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

    try:
        user = CustomUser.objects.get(id=user_id)
        verification = OTPVerification.objects.get(user=user)
    except (CustomUser.DoesNotExist, OTPVerification.DoesNotExist):
        return redirect('register')

    is_console_mode = settings.EMAIL_BACKEND.endswith('console.EmailBackend')

    if request.method == 'POST':
        if 'cancel' in request.POST:
            try:
                if not user.is_active:
                    user.delete()
            except Exception:
                pass
            request.session.pop('verification_user_id', None)
            return redirect('register')

        otp_entered = request.POST.get('otp', '').strip()
        if verification.otp == otp_entered and verification.is_valid():
            user.is_active = True
            user.save()
            verification.delete()
            del request.session['verification_user_id']
            login(request, user)
            return redirect('dashboard_home')
        else:
            return render(request, 'users/verify_otp.html', {
                'error': 'Invalid or expired OTP. Please check the code and try again.',
                'user_email': user.email,
                'debug_otp': verification.otp,
                'is_console_mode': is_console_mode,
            })

    return render(request, 'users/verify_otp.html', {
        'user_email': user.email,
        'debug_otp': verification.otp,
        'is_console_mode': is_console_mode,
    })


def resend_otp_view(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        return redirect('register')

    try:
        from django.utils import timezone
        user = CustomUser.objects.get(id=user_id)
        new_otp = get_random_string(length=6, allowed_chars='0123456789')
        verification, created = OTPVerification.objects.update_or_create(
            user=user, defaults={'otp': new_otp}
        )
        verification.created_at = timezone.now()
        verification.save()

        try:
            send_mail(
                'FoodBridge AI - Account Verification Code (Resent)',
                f'Your new 6-digit OTP verification code is: {new_otp}\n\nThis code is valid for 10 minutes.\n\nThank you,\nFoodBridge AI Team',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"[EMAIL WARNING] Could not dispatch email via SMTP: {e}")

        from django.contrib import messages
        messages.success(request, 'A fresh 6-digit OTP code has been generated.')
    except CustomUser.DoesNotExist:
        return redirect('register')

    return redirect('verify_otp')


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
