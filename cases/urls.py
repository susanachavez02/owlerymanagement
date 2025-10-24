from django.urls import path
from . import views

app_name = 'cases'

urlpatterns = [
    # --- Admin Workflow Management ---
    path('workflows/', views.workflow_list_view, name='workflow-list'),
    path('workflows/create/', views.workflow_create_view, name='workflow-create'),
    path('workflows/<int:pk>/', views.workflow_detail_view, name='workflow-detail'),
    path('workflows/stage/create/<int:workflow_pk>/', views.stage_create_view, name='stage-create'),

    # --- NEW: Admin Template Management ---
    path('templates/', views.template_list_view, name='template-list'),
    path('templates/upload/', views.template_upload_view, name='template-upload'),
    path('contract-template/', views.contract_template_view, name='contract-template'),

    # --- Admin Case Management ---
    # Admin: Create a new case
    path('create/', views.case_create_view, name='case-create'),
    # Admin: List all cases
    path('/', views.case_list_view, name='case-list'),

    # --- Billing & Invoicing URLs ---
    path('<int:case_pk>/billing/', views.billing_view, name='billing-dashboard'),
    path('invoice/<int:pk>/', views.invoice_detail_view, name='invoice-detail'),
    
    # --- User-Facing Case Views ---
    # View details for a single case
    # <int:pk> captures the ID from the URL (e.g., /cases/1/)
    path('<int:pk>/', views.case_detail_view, name='case-detail'),
    # View/Download a document and log it
    # e.g., /cases/document/5/view/
    path('document/<int:doc_pk>/view/', views.document_view_and_log, name='document-view'),

    # --- Advance Case Stage ---
    path('<int:case_pk>/advance-stage/', views.advance_stage_view, name='advance-stage'),

    # --- Generate Document ---
    path('<int:case_pk>/generate-document/', views.generate_document_view, name='generate-document'),
    
    path('document/<int:doc_pk>/view/', views.document_view_and_log, name='document-view'),
    path('<int:case_pk>/advance-stage/', views.advance_stage_view, name='advance-stage'),

    # --- E-Signature URLs ---
    path('document/<int:doc_pk>/request-signature/', views.signature_request_view, name='signature-request'),
    path('document/sign/<uuid:token>/', views.signing_page_view, name='signing-page'),
]
