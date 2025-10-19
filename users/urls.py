from django.urls import path
from . import views  # We will create these views in the next step

# This line gives your app a "namespace"
# It helps you refer to these URLs without conflict
app_name = 'users'

urlpatterns = [
    # URL for the admin to create an onboarding key
    # e.g., /users/create-key/
    path('create-key/', views.admin_create_key_view, name='create-key'),

    # Public URL for a new user to enter their key
    # e.g., /users/register/
    path('register/', views.register_with_key_view, name='register'),
    
    # Public URL for the user to set their password once the key is validated
    # e.g., /users/set-password/a-long-uuid-key/
    path('set-password/<uuid:key>/', views.set_password_view, name='set-password'),
]