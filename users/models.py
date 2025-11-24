# Create your models here.
from django.db import models
from django.contrib.auth.models import User
import uuid # To generate a secure, random key for the OnboardingKey model
from django.utils import timezone # We'll need this for the expiration time

# Model 1: UserProfile Database (users_userprofile)
class UserProfile(models.Model):
    # This links the profile to the built-in Django User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    firm_role = models.CharField(max_length=100, blank=True)
    
    # ADD THIS LINE:
    profile_picture = models.ImageField(default='default_profile.png', upload_to='profile_pics', blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'

# Model 2: Role
class Role(models.Model):
    # 'Admin', 'Attorney', 'Client' 
    name = models.CharField(max_length=100, unique=True)
    
    # This links the roles to many users. This is the key!
    users = models.ManyToManyField(User, related_name='roles', blank=True)

    def __str__(self):
        return self.name

# Model 3: OnboardingKey - defines a table to store temporary, one-time-use keys for new users
class OnboardingKey(models.Model):
    # A fied that stores a Universally Unique Identifier, generates a random key every time
    key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Links to the User account the Admin created 
    user_to_be_assigned = models.OneToOneField(User, on_delete=models.CASCADE)
    
    is_used = models.BooleanField(default=False)
    
    # We set a default expiration time for the key, prevents old, forgotten onboarding links from being secuirty risks
    expires_at = models.DateTimeField() # 

    roles = models.ManyToManyField(Role, blank=True, help_text="Roles to assign when user completes onboarding")
    
    def is_valid(self):
        """Checks if the key is unused and not expired."""
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"Key for {self.user_to_be_assigned.username}"