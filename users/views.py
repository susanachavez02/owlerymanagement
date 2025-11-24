# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from .models import OnboardingKey, UserProfile, Role
from .forms import AdminCreateKeyForm, RegisterWithKeyForm, UserSetPasswordForm, ClientReassignmentForm, UserCreationAdminForm, UserEditAdminForm
from cases.models import Case, CaseAssignment
from django.urls import reverse
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string

# --- NEW: Homepage View ---
def homepage_view(request):
    # If user is already logged in, send them to their dashboard
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    # Otherwise, show the public homepage
    return render(request, 'users/landing_page.html')

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
            roles = form.cleaned_data['roles']
            hours = form.cleaned_data['expires_in_hours']
            
            # Delete any old, unused keys for this user first
            OnboardingKey.objects.filter(user_to_be_assigned=user, is_used=False).delete()
            
            # Create the new key
            key_instance = OnboardingKey.objects.create(
                user_to_be_assigned=user,
                expires_at=timezone.now() + timezone.timedelta(hours=hours)
            )
            
            #Assign the roles to the key
            key_instance.roles.set(roles)

            # Show a success message
            messages.success(request, f"Key generated for {user.username}. The setup link is:")
            
            # Build the full, absolute URL for the setup link
            setup_link = request.build_absolute_uri(
                f'/users/set-password/{key_instance.key}/'
            )
            messages.info(request, setup_link) # Show the link

            # Send email if user has an email address
            if user.email:
                subject = "Your Owlery Account Invitation"
                
                # Use the template context
                context = {
                    'user_name': user.first_name or user.username,
                    'setup_link': setup_link,
                    'hours': hours,
                }
                
                # Render the email template
                message = render_to_string('users/onboarding_email.txt', context)
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,  # Uses the Gmail from .env
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, f"Key generated for {user.username}. Email sent to {user.email}.")
            else:
                # No email provided, just show the link in messages
                messages.success(request, f"Key generated for {user.username}. No email on file. The setup link is:")
                messages.info(request, setup_link)
            
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

            # Assign the roles from the OnboardingKey
            user.roles.set(key_instance.roles.all())
            
            # Mark the key as used
            key_instance.is_used = True
            key_instance.save()
            
            # Log the user in automatically
            login(request, user)
            messages.success(request, "Your password has been set and you are now logged in.")
            
            # TODO: Redirect to the correct dashboard (client or attorney)
            return redirect('users:dashboard') # Redirect to the homepage for now
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
        return redirect('cases:case-dashboard')
        
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
        return redirect('users:logout')
    
# --- STEP 33: USER MANAGEMENT VIEW
# ---
@login_required
@user_passes_test(is_admin)
def user_management_list_view(request):
    User = get_user_model()
    
    # 1. Start with all users
    users = User.objects.all().order_by('-date_joined')
    
    # 2. Search Filter (checks username, first name, last name, email)
    search_query = request.GET.get('q', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # 3. Role Filter (checks the Role model relation)
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(roles__name=role_filter)
    
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter
    }
    return render(request, 'users/user_management_list.html', context)

# --- Toggle User Active Status ---
@login_required
@user_passes_test(is_admin)
def toggle_user_active_view(request, user_pk):
    user_to_toggle = get_object_or_404(User, pk=user_pk)
    
    # Prevent admin from deactivating themselves
    if user_to_toggle == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('user-list')

    # Flip the is_active status
    user_to_toggle.is_active = not user_to_toggle.is_active
    user_to_toggle.save()
    
    status = "activated" if user_to_toggle.is_active else "deactivated"
    messages.success(request, f"User '{user_to_toggle.username}' has been {status}.")
    return redirect('user-list')

# --- Admin-Forced Password Reset ---
@login_required
@user_passes_test(is_admin)
def admin_reset_password_view(request, user_pk):
    user_to_reset = get_object_or_404(User, pk=user_pk)
    
    # We will re-use your OnboardingKey system
    
    # 1. Delete any old, unused keys for this user
    OnboardingKey.objects.filter(user_to_be_assigned=user_to_reset, is_used=False).delete()
    
    # 2. Create a new key that expires in 24 hours
    key_instance = OnboardingKey.objects.create(
        user_to_be_assigned=user_to_reset,
        expires_at=timezone.now() + timezone.timedelta(hours=24)
    )
    
    # 3. Build the reset link
    reset_link = request.build_absolute_uri(
        reverse('users:set-password', kwargs={'key': key_instance.key})
    )
    
    messages.success(request, f"New password reset link generated for {user_to_reset.username}.")
    messages.info(request, f"Please send this link to the user: {reset_link}")
    return redirect('user-list')

# --- STEP 35: CLIENT REASSIGNMENT VIEW
# ---
@login_required
@user_passes_test(is_admin)
def client_reassignment_view(request):
    cases_to_reassign = None
    from_attorney = None
    to_attorney = None

    if request.method == 'POST':
        # --- Handle the SECOND POST (Confirmation) ---
        if 'confirm_reassignment' in request.POST:
            from_attorney_id = request.POST.get('from_attorney_id')
            to_attorney_id = request.POST.get('to_attorney_id')
            case_ids_to_move = request.POST.getlist('case_ids') # Get list of checked case IDs

            if not from_attorney_id or not to_attorney_id or not case_ids_to_move:
                messages.error(request, "Missing information for reassignment.")
                return redirect('client-reassignment')

            try:
                from_attorney = User.objects.get(pk=from_attorney_id)
                to_attorney = User.objects.get(pk=to_attorney_id)

                with transaction.atomic():
                    updated_count = 0
                    for case_id in case_ids_to_move:
                        # Find the assignment linking the case to the FROM attorney
                        assignment = CaseAssignment.objects.filter(
                            case__pk=case_id,
                            user=from_attorney
                        ).first()

                        if assignment:
                            # Update the user field to the TO attorney
                            assignment.user = to_attorney
                            assignment.save()
                            updated_count += 1

                messages.success(request, f"Successfully reassigned {updated_count} case(s) from {from_attorney.username} to {to_attorney.username}.")
                return redirect('user-list')

            except User.DoesNotExist:
                messages.error(request, "Invalid attorney ID provided.")
                return redirect('client-reassignment')
            except Exception as e:
                messages.error(request, f"An error occurred during reassignment: {e}")
                return redirect('client-reassignment')

        # --- Handle the FIRST POST (Attorney Selection) ---
        else:
            form = ClientReassignmentForm(request.POST)
            if form.is_valid():
                from_attorney = form.cleaned_data['from_attorney']
                to_attorney = form.cleaned_data['to_attorney']

                # Find all active cases assigned to the 'from_attorney'
                cases_to_reassign = Case.objects.filter(
                    assignments__user=from_attorney,
                    is_archived=False
                ).distinct() # Use distinct to avoid duplicates if multiple assignments exist

                if not cases_to_reassign.exists():
                    messages.warning(request, f"{from_attorney.username} has no active cases to reassign.")
                    # Show the form again, blank
                    form = ClientReassignmentForm()
            # If form is invalid, it will fall through and render again with errors
    
    # --- Handle GET request (or if form validation failed) ---
    if not cases_to_reassign: # Only create a blank form if we aren't showing the confirmation step
        form = ClientReassignmentForm()

    context = {
        'form': form if not cases_to_reassign else None, # Only show form on first step
        'cases_to_reassign': cases_to_reassign,
        'from_attorney': from_attorney,
        'to_attorney': to_attorney,
    }
    return render(request, 'users/client_reassignment.html', context)

# --- NEW: Admin User Creation View ---
@login_required
@user_passes_test(is_admin)
def user_create_view(request):
    if request.method == 'POST':
        form = UserCreationAdminForm(request.POST)
        if form.is_valid():
            # The form's save method handles setting is_active=False
            # and setting an unusable password
            new_user = form.save()
            
            messages.success(request, f"User '{new_user.username}' created successfully. Now generate an onboarding key for them.")
            # Redirect to the key generation page
            return redirect('users:create-key')
    else:
        # Show a blank form on GET request
        form = UserCreationAdminForm()

    context = {
        'form': form
    }
    return render(request, 'users/user_create.html', context)

# --- Admin User Edit View ---
@login_required
@user_passes_test(is_admin)
def user_edit_view(request, user_pk):
    user_to_edit = get_object_or_404(User, pk=user_pk)

    if request.method == 'POST':
        form = UserEditAdminForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save() # The form's save method handles updating roles
            messages.success(request, f"User '{user_to_edit.username}' updated successfully.")
            return redirect('user-list')
    else:
        # Populate the form with the user's current data on GET
        form = UserEditAdminForm(instance=user_to_edit)

    context = {
        'form': form,
        'user_to_edit': user_to_edit # Pass user for context in template
    }
    return render(request, 'users/user_edit.html', context)



@login_required
def profile_view(request, user_pk):
    # Get the user whose profile is being viewed
    profile_user = get_object_or_404(User.objects.prefetch_related('roles', 'profile'), pk=user_pk)
    
    # Get the user who is doing the viewing
    viewer = request.user
    
    # Get roles for easier checking (using the context processor logic here is fine too)
    viewer_roles = set(viewer.roles.values_list('name', flat=True))
    profile_roles = set(profile_user.roles.values_list('name', flat=True))
    
    # --- Permission Logic ---
    can_view = False
    
    if 'Admin' in viewer_roles:
        # Admins can see everyone
        can_view = True
    elif 'Attorney' in viewer_roles:
        # Attorneys can see Admins and Clients
        if 'Admin' in profile_roles or 'Client' in profile_roles:
            can_view = True
    elif 'Client' in viewer_roles:
        # Clients can see Attorneys
        if 'Attorney' in profile_roles:
            can_view = True
            
    # Also allow users to view their own profile
    if viewer == profile_user:
        can_view = True
        
    # --- Render or Deny ---
    if can_view:
        context = {
            'profile_user': profile_user,
        }
        return render(request, 'users/profile_detail.html', context)
    else:
        messages.error(request, "You do not have permission to view this profile.")
        # Redirect to the viewer's own dashboard
        return redirect('users:dashboard')