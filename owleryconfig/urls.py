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
    
    # --- NEW: Admin Reporting URL ---
    path('reports/', case_views.reporting_view, name='reporting-dashboard'),

    # This forwards any URL starting with 'messages/'
    # to the 'communication' app's urls.py file.
    path('messages/', include('communication.urls')),

    # --- STRIPE URLS ---
    path('create-checkout-session/<int:pk>/', case_views.create_checkout_session_view, name='create-checkout-session'),
    path('stripe-webhook/', case_views.stripe_webhook_view, name='stripe-webhook'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)