from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from .models import OnboardingKey, Role
import uuid

class AdminCreateKeyForm(forms.Form):
    # This field lets the admin pick a user from a dropdown list.
    # We only show users who are NOT superusers and are not yet active.
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_superuser=False, is_active=False),
        label="Select User to Onboard",
        help_text="Select the user account to generate an activation key for."
    )
    # This field lets the admin set how long the key is valid.
    expires_in_hours = forms.IntegerField(
        initial=24, 
        min_value=1,
        label="Key valid for (hours)"
    )

class RegisterWithKeyForm(forms.Form):
    # This field expects the user to paste in the UUID.
    key = forms.UUIDField(
        label="Onboarding Key",
        help_text="Please enter the onboarding key you received."
    )

    def clean_key(self):
        """
        This is a custom validation method. It runs after the basic
        UUID check and makes sure the key is valid and usable.
        """
        key_data = self.cleaned_data['key']
        try:
            # Find the key in the database
            key_instance = OnboardingKey.objects.get(key=key_data)
            
            # Check if it's valid (not used and not expired)
            if not key_instance.is_valid():
                raise forms.ValidationError("This key has expired or has already been used.")
                
        except OnboardingKey.DoesNotExist:
            raise forms.ValidationError("The key you entered is not valid.")
        
        # If all checks pass, return the key instance itself
        return key_instance

class UserSetPasswordForm(SetPasswordForm):
    """
    This is Django's built-in SetPasswordForm. We are just inheriting
    from it to use its built-in logic for checking that the two
    password fields match.
    """
    pass

# --- NEW: Client Reassignment Form ---
class ClientReassignmentForm(forms.Form):
    from_attorney = forms.ModelChoiceField(
        queryset=User.objects.filter(roles__name='Attorney'),
        label="Reassign Cases FROM this Attorney",
        required=True
    )
    to_attorney = forms.ModelChoiceField(
        queryset=User.objects.filter(roles__name='Attorney'),
        label="Reassign Cases TO this Attorney",
        required=True
    )

    def clean(self):
        """
        Custom validation to ensure the 'from' and 'to'
        attorneys are not the same person.
        """
        cleaned_data = super().clean()
        from_attorney = cleaned_data.get("from_attorney")
        to_attorney = cleaned_data.get("to_attorney")

        if from_attorney and to_attorney:
            if from_attorney == to_attorney:
                raise forms.ValidationError(
                    "The 'From' and 'To' attorneys cannot be the same person."
                )
        return cleaned_data
    
# --- Admin User Creation Form ---
class UserCreationAdminForm(forms.ModelForm):
    # Field to select roles for the new user
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Assign Roles"
    )

    class Meta:
        model = User
        # Fields admin needs to fill in
        fields = ['username', 'email', 'first_name', 'last_name']
        help_texts = {
            'username': 'Required. Letters, digits and @/./+/-/_ only.',
        }

    def save(self, commit=True):
        # Override save to ensure user is inactive and has no password initially
        user = super().save(commit=False)
        user.is_active = False
        user.set_unusable_password() # Important: Don't set a password here
        if commit:
            user.save()
            # Save the many-to-many relationship for roles
            self.save_m2m()
        return user
    
# --- Admin User Edit Form ---
class UserEditAdminForm(forms.ModelForm):
    # Field to select/change roles for the user
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Assign Roles"
    )

    class Meta:
        model = User
        # Fields admin can edit
        fields = ['username', 'email', 'first_name', 'last_name']
        help_texts = {
            'username': 'Required. Letters, digits and @/./+/-/_ only.',
        }

    def __init__(self, *args, **kwargs):
        # Need to pre-populate roles checkbox correctly
        super().__init__(*args, **kwargs)
        if self.instance.pk: # Check if we are editing an existing user
            self.fields['roles'].initial = self.instance.roles.all()

    def save(self, commit=True):
        # We need to save the user first, then update roles
        user = super().save(commit=False)
        if commit:
            user.save()
            # Manually update the many-to-many relationship for roles
            user.roles.set(self.cleaned_data['roles'])
            self.save_m2m() # Although maybe redundant now
        return user
    
# --- Admin User Delete Form ---
class UserDeleteAdminForm(forms.Form):
    confirm_username = forms.CharField(
        label="Type the username to confirm deletion",
        help_text="This action cannot be undone."
    )

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

    def clean_confirm_username(self):
        entered_username = self.cleaned_data['confirm_username']
        if self.user_instance and entered_username != self.user_instance.username:
            raise forms.ValidationError("The username does not match.")
        return entered_username