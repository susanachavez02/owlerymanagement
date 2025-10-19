from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from .models import OnboardingKey
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