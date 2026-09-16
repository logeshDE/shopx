from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator

from .models import User, Address
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, AddressForm


# ── Helpers ────────────────────────────────────────────────────

def send_verification_email(user, request):
    token = default_token_generator.make_token(user)
    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    url   = request.build_absolute_uri(f'/accounts/verify-email/{uid}/{token}/')
    send_mail(
        subject='Verify your email — ShopX',
        message=f'Hi {user.first_name},\n\nVerify your email:\n{url}\n\nExpires in 24 hours.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# ── Auth ───────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        send_verification_email(user, request)
        messages.success(request, 'Account created! Check your email to verify.')
        return redirect('accounts:login')
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, uidb64, token):
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        messages.success(request, 'Email verified! You can now log in.')
        return redirect('accounts:login')

    messages.error(request, 'Verification link is invalid or has expired.')
    return redirect('accounts:register')


def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = User.objects.get(email=email)
            if user.is_email_verified:
                messages.info(request, 'Your email is already verified.')
            else:
                send_verification_email(user, request)
                messages.success(request, 'Verification email resent!')
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email.')
    return redirect('accounts:login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
        )
        if user:
            if not user.is_email_verified:
                messages.warning(request, 'Please verify your email before logging in.')
                return redirect('accounts:login')
            # Save guest session key BEFORE login() cycles the session
            request._pre_login_session_key = request.session.session_key
            login(request, user)
            return redirect(request.GET.get('next') or 'products:home')
        messages.error(request, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


# ── Profile ────────────────────────────────────────────────────

@login_required
def profile_view(request):
    user = request.user
    from .models import Profile
    profile, _ = Profile.objects.get_or_create(user=user)
    form = ProfileUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        initial={'first_name': user.first_name, 'last_name': user.last_name, 'phone': user.phone},
    )
    if request.method == 'POST' and form.is_valid():
        user.first_name = form.cleaned_data['first_name']
        user.last_name  = form.cleaned_data['last_name']
        user.phone      = form.cleaned_data['phone']
        user.save(update_fields=['first_name', 'last_name', 'phone'])
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {
        'form': form,
        'addresses': user.addresses.all(),
    })


# ── Addresses ──────────────────────────────────────────────────

@login_required
def add_address(request):
    form = AddressForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if address.is_default:
            request.user.addresses.update(is_default=False)
        address.save()
        messages.success(request, 'Address added.')
        return redirect('accounts:profile')
    return render(request, 'accounts/address_form.html', {'form': form, 'action': 'Add'})


@login_required
def edit_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address)
    if request.method == 'POST' and form.is_valid():
        if form.cleaned_data.get('is_default'):
            request.user.addresses.exclude(pk=pk).update(is_default=False)
        form.save()
        messages.success(request, 'Address updated.')
        return redirect('accounts:profile')
    return render(request, 'accounts/address_form.html', {'form': form, 'action': 'Edit'})


@login_required
def delete_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted.')
    return redirect('accounts:profile')


@login_required
def set_default_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    request.user.addresses.update(is_default=False)
    address.is_default = True
    address.save(update_fields=['is_default'])
    messages.success(request, 'Default address updated.')
    return redirect('accounts:profile')