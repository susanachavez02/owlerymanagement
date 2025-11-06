"""
URL configuration for owleryconfig project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users import views as user_views
from cases import views as case_views

urlpatterns = [
    path('', user_views.homepage_view, name='homepage'),

    path("admin/", admin.site.urls),
    path('users/', include('users.urls')),
    path('cases/', include('cases.urls')),

    # --- User Management URL ---
    path('management/users/', user_views.user_management_list_view, name='user-list'),
    path('management/users/create/', user_views.user_create_view, name='user-create'),
    path('management/users/<int:user_pk>/edit/', user_views.user_edit_view, name='user-edit'), 
    # Toggle a user's active status (deactivate/reactivate)
    path('management/users/<int:user_pk>/toggle-active/', user_views.toggle_user_active_view, name='user-toggle-active'),
    # Admin generates a password reset link
    path('management/users/<int:user_pk>/reset-password/', user_views.admin_reset_password_view, name='user-reset-password'),
    path('profile/<int:user_pk>/', user_views.profile_view, name='profile-view'), 

    # --- Client Reassignment URL ---
    path('management/reassign/', user_views.client_reassignment_view, name='client-reassignment'),

    # --- MESSAGES URLS ---
    # This forwards any URL starting with 'messages/'
    # to the 'communication' app's urls.py file.
    path('messages/', include('communication.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)