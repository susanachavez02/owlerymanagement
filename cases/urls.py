from django.urls import path
from . import views
from .views import (
    ContractTemplateListCreateView,
    ContractTemplateRetrieveUpdateDestroyView,
    ContractTemplateDownloadView
)

app_name = 'cases'

urlpatterns = [
    # --- Calendar API  ---
    path('api/calendar-events/', views.calendar_events_api, name='calendar-events-api'),
    path('calendar/', views.calendar_view, name='calendar'),

    # User Management Paths
    path('clients/', views.client_list_view, name='client-list'),
    path('attorneys/', views.attorney_list_view, name='attorney-list'),
    path('profile/<int:pk>/', views.user_profile_view, name='user-profile'),

    # --- Admin Workflow Management ---
    path('workflows/', views.workflow_list_view, name='workflow-list'),
    path('workflows/create/', views.workflow_create_view, name='workflow-create'),
    path('workflows/<int:pk>/', views.workflow_detail_view, name='workflow-detail'),
    path('workflows/stage/create/<int:workflow_pk>/', views.stage_create_view, name='stage-create'),

    # --- Meeting Management ---
    path('create-meeting/', views.create_meeting_view, name='create-meeting'),
    path('<int:pk>/create-meeting/', views.create_meeting_view, name='create-meeting'),  # From case detail
    path('<int:meeting_pk>/edit-meeting/', views.edit_meeting_view, name='edit-meeting'),  # From case detail

    # --- NEW: Admin Template Management ---
    path('templates/generate/', views.generate_document_view, name='template-generation'),
    path('templates/upload/', views.template_upload_view, name='template-upload'),
    path('contract-template/', views.contract_template_view, name='contract-template'),

    # --- Admin Case Management ---
    # Admin: Create a new case
    path('create/', views.case_create_view, name='case-create'),
    # Admin: List all cases
    path('case-dashboard/', views.case_dashboard_view, name='case-dashboard'),
    path('case/<int:pk>/delete/', views.case_delete_view, name='case-delete'),

    # --- User-Facing Case Views ---
    # View details for a single case
    # <int:pk> captures the ID from the URL (e.g., /cases/1/)
    path('<int:pk>/', views.case_detail_view, name='case-detail'),
    # View/Download a document and log it
    # e.g., /cases/document/5/view/
    path('document/<int:doc_pk>/view/', views.document_view_and_log, name='document-view'),
    path('api/templates/', ContractTemplateListCreateView.as_view(), name='template-list-create'),
    path('api/templates/<int:pk>/', ContractTemplateRetrieveUpdateDestroyView.as_view(), name='template-detail' ),
    path('templates/', views.template_list, name='template-list'),
    path('api/convert-pdf/', views.convert_pdf_api_view, name='api-convert-pdf'),   
    path('api/templates/<int:pk>/download/', views.ContractTemplateDownloadView.as_view(), name='template-download'),
    path('api/contract-template/<int:pk>/content/', views.get_db_template_content, name='db-template-content'),

    # Case Directory
    path('cases/', views.case_directory_view, name='case-directory'),
    # 1. Initial access, no case_pk provided (shows empty form with dropdown)
    path('management/reassign/', views.case_reassign_management, name='case-reassign-list'),
    path('management/list/', views.user_management_view, name='user-management-list'),

# 2. Case-specific access, case_pk is provided (after selecting from dropdown or via direct link)
    path('management/reassign/<int:case_pk>/', views.case_reassign_management, name='case-reassign'),
    # --- Advance Case Stage ---
    path('<int:case_pk>/advance-stage/', views.advance_stage_view, name='advance-stage'),

    # --- Generate Document ---
    path('<int:case_pk>/generate-document/', views.generate_document_view, name='generate-document'),
    path('<int:case_pk>/advance-stage/', views.advance_stage_view, name='advance-stage'),

    # --- E-Signature URLs ---
    path('document/<int:doc_pk>/request-signature/', views.signature_request_view, name='signature-request'),
    path('document/sign/<uuid:token>/', views.signing_page_view, name='signing-page'),

    # Public Form
    path('request-consultation/', views.request_consultation_view, name='request-consultation'),
    
    # Attorney Actions
    path('consultation/<int:pk>/', views.consultation_detail_view, name='consultation-detail'),
    path('consultation/<int:pk>/schedule/', views.schedule_consultation_action, name='schedule-consultation'),
    path('consultation/<int:pk>/update/<str:status>/', views.update_consultation_status, name='update-consultation'),
]
