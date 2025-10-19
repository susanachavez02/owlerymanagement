from django.urls import path
from . import views

app_name = 'cases'

urlpatterns = [
    # Admin: Create a new case
    path('create/', views.case_create_view, name='case-create'),

    # Admin: List all cases
    path('', views.case_list_view, name='case-list'),
    
    # NEW: View details for a single case
    # <int:pk> captures the ID from the URL (e.g., /cases/1/)
    path('<int:pk>/', views.case_detail_view, name='case-detail'),

    # NEW: View/Download a document and log it
    # e.g., /cases/document/5/view/
    path('document/<int:doc_pk>/view/', views.document_view_and_log, name='document-view'),
]