# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import OnboardingKey, UserProfile, Role
from .forms import AdminCreateKeyForm, RegisterWithKeyForm, UserSetPasswordForm
from cases.models import Case

# --- NEW: Homepage View ---
def homepage_view(request):
    # If user is already logged in, send them to their dashboard
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    # Otherwise, show the public homepage
    return render(request, 'users/homepage.html')

# This is a "test function" to check if a user is an admin
def is_admin(user):
    return user.is_authenticated and user.roles.filter(name='Admin').exists()

# --- View 1: Admin Create Key ---

@login_required
@user_passes_test(is_admin)
def admin_create_key_view(request):
    if request.method == 'POST':
        form = AdminCreateKeyForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            hours = form.cleaned_data['expires_in_hours']
            
            # Delete any old, unused keys for this user first
            OnboardingKey.objects.filter(user_to_be_assigned=user, is_used=False).delete()
            
            # Create the new key
            key_instance = OnboardingKey.objects.create(
                user_to_be_assigned=user,
                expires_at=timezone.now() + timezone.timedelta(hours=hours)
            )
            
            # Show a success message
            messages.success(request, f"Key generated for {user.username}. The setup link is:")
            
            # Build the full, absolute URL for the setup link
            setup_link = request.build_absolute_uri(
                f'/users/set-password/{key_instance.key}/'
            )
            messages.info(request, setup_link) # Show the link
            
            return redirect('users:create-key') # Redirect back to the same page
    else:
        form = AdminCreateKeyForm()
        
    return render(request, 'users/admin_create_key.html', {'form': form})

# --- View 2: Register With Key ---

def register_with_key_view(request):
    if request.method == 'POST':
        form = RegisterWithKeyForm(request.POST)
        if form.is_valid():
            # The form's clean_key method already validated the key
            # and returned the key *instance*
            key_instance = form.cleaned_data['key']
            
            # Redirect to the set password page, passing the key in the URL
            return redirect('users:set-password', key=key_instance.key)
    else:
        form = RegisterWithKeyForm()
        
    return render(request, 'users/register_with_key.html', {'form': form})

# --- View 3: Set Password ---

def set_password_view(request, key):
    # Get the key from the URL, or show a 404 (Not Found) error
    key_instance = get_object_or_404(OnboardingKey, key=key)
    
    # Check if the key is valid BEFORE showing the form
    if not key_instance.is_valid():
        messages.error(request, "This setup link has expired or has already been used.")
        return redirect('users:register')
        
    user = key_instance.user_to_be_assigned

    if request.method == 'POST':
        form = UserSetPasswordForm(user, request.POST)
        if form.is_valid():
            # Save the new password to the user
            form.save()
            
            # Activate the user
            user.is_active = True
            user.save()
            
            # Mark the key as used
            key_instance.is_used = True
            key_instance.save()
            
            # Log the user in automatically
            login(request, user)
            
            messages.success(request, "Your password has been set and you are now logged in.")
            
            # TODO: Redirect to the correct dashboard (client or attorney)
            return redirect('/') # Redirect to the homepage for now
    else:
        form = UserSetPasswordForm(user)
        
    return render(request, 'users/set_password.html', {'form': form, 'key': key})

# --- NEW: Dashboard View ---

@login_required
def dashboard_view(request):
    user = request.user
    
    # --- Check Roles ---
    
    # 1. Is the user an Admin?
    if user.roles.filter(name='Admin').exists():
        # Admins just see the main case list.
        return redirect('cases:case-list')
        
    # 2. Is the user an Attorney?
    elif user.roles.filter(name='Attorney').exists():
        # Get all cases assigned to this attorney
        assigned_cases = Case.objects.filter(assignments__user=user).order_by('-date_filed')
        
        context = {
            'assigned_cases': assigned_cases,
            'is_attorney': True
        }
        return render(request, 'users/dashboard.html', context)
        
    # 3. Is the user a Client?
    elif user.roles.filter(name='Client').exists():
        # Get all cases assigned to this client
        assigned_cases = Case.objects.filter(assignments__user=user).order_by('-date_filed')
        
        context = {
            'assigned_cases': assigned_cases,
            'is_client': True
        }
        return render(request, 'users/dashboard.html', context)
    
    # 4. Fallback
    else:
        # If user has no roles, send them to the login page with an error.
        messages.error(request, "Your account is not yet configured. Please contact an administrator.")
        return redirect('logout')
    
