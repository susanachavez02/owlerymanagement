from django.contrib import admin
from .models import Role, UserProfile, OnboardingKey # Import your models

# Register your models here to make them visible in the admin
admin.site.register(Role)
admin.site.register(UserProfile)
admin.site.register(OnboardingKey)