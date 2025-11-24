from django.urls import path
from django.contrib.auth import views as auth_views
from . import views  # We will create these views in the next step

# This line gives your app a "namespace"
# It helps you refer to these URLs without conflict
app_name = 'users'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # URL for the admin to create an onboarding key
    # e.g., /users/create-key/
    path('create-key/', views.admin_create_key_view, name='create-key'),

    # Public URL for a new user to enter their key
    # e.g., /users/register/
    path('register/', views.register_with_key_view, name='register'),
    
    # Public URL for the user to set their password once the key is validated
    # e.g., /users/set-password/a-long-uuid-key/
    path('set-password/<uuid:key>/', views.set_password_view, name='set-password'),
    path('user-edit/<int:pk>/', views.user_edit_view, name='user-edit'),
]