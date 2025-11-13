from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.db import models
import io
from docx import Document as DocxDocument
from django.core.files.base import ContentFile
# We need to import the admin test function from our 'users' app

# --- Model Imports ---
from .models import (
    Case, CaseAssignment, Document, DocumentLog,
    CaseWorkflow, CaseStage, Template, 
    SignatureRequest, CaseStageLog, 
)
from django.db.models import Sum, Count, Avg, F
from users.models import Role

# --- Form Imports ---
from .forms import (
    CaseCreateForm, DocumentUploadForm,
    WorkflowCreateForm, StageCreateForm, 
    TemplateUploadForm
)

from users.views import is_admin
from .decorators import user_is_assigned_to_case

# --- Django's File handling utilities ---
from django.core.files.base import ContentFile
from django.conf import settings # <-- Import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import json
from django.conf import settings

# --- HELPER FUNCTION FOR DOCX ---
def docx_find_and_replace(doc, context):
    """
    Finds and replaces text in a .docx file, preserving formatting.
    Placeholders must be in the format {{key_name}}.
    """
    # Combine paragraphs from the main body and all table cells
    all_paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_paragraphs.extend(cell.paragraphs)
    
    for p in all_paragraphs:
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}" # Creates {{key_name}}
            
            # We must iterate over 'runs' to preserve formatting (bold, etc.)
            # A simple p.text.replace() would wipe all formatting.
            if placeholder in p.text:
                for run in p.runs:
                    if placeholder in run.text:
                        run.text = run.text.replace(placeholder, str(value))
    return doc

# --- View 1: Case List (Admin) ---

@login_required
@user_passes_test(is_admin)
def case_dashboard_view(request):
    # This assumes you have a way to filter for "active" cases
    cases_list = Case.objects.filter(is_archived=False).order_by('-date_filed') 
    
    # Example logic for stat cards (you'll need to adjust this)
    active_count = cases_list.count()
    
    # This requires a 'status' field on your SignatureRequest model
    pending_count = SignatureRequest.objects.filter(status='pending').count() 

    context = {
        'cases': cases_list,
        'active_case_count': active_count,
        'pending_signature_count': pending_count,
    }
    return render(request, 'cases/case_list.html', context)

# --- View 2: Case Create (Admin) ---

@login_required
@user_passes_test(is_admin)
def case_create_view(request):
    if request.method == 'POST':
        form = CaseCreateForm(request.POST)
        if form.is_valid():
            case = form.save() # We can save directly now

            # If a workflow was assigned, set the current_stage
            # to the first stage in that workflow (order=1).
            if case.workflow:
                first_stage = case.workflow.stages.filter(order=1).first()
                if first_stage:
                    case.current_stage = first_stage
                    case.save() # Save the change

                    CaseStageLog.objects.create(case=case, stage=first_stage)

            # Step 2: Get the attorney and client from the form's data
            attorney = form.cleaned_data['attorney']
            client = form.cleaned_data['client']
            
            # Step 3: Create the CaseAssignment links
            CaseAssignment.objects.create(case=case, user=attorney)
            CaseAssignment.objects.create(case=case, user=client)
            
            messages.success(request, f"Successfully created case: {case.case_title}")
            return redirect('cases:case-list') # Redirect to the new list
    else:
        # If it's a GET request, just show a blank form
        form = CaseCreateForm()
        
    context = {
        'form': form
    }
    return render(request, 'cases/case_create.html', context)



# --- View 3: Case Detail (SECURED) ---
@login_required
@user_is_assigned_to_case
def case_detail_view(request, pk):
    case = get_object_or_404(Case, pk=pk)
    next_stage = None
    
    if request.method == 'POST':
        
        # --- Check which form was submitted ---
        
        # Check if the 'upload_document' button was pressed
        if 'upload_document' in request.POST:
            upload_form = DocumentUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                doc = upload_form.save(commit=False) 
                doc.case = case
                doc.uploaded_by = request.user
                doc.save()
                DocumentLog.objects.create(document=doc, user=request.user, action="Uploaded")
                messages.success(request, f"Document '{doc.title}' uploaded successfully.")
                return redirect('cases:case-detail', pk=case.pk)
        
    
    # --- GET Request Logic ---
    documents = case.documents.all().order_by('-id')
    assignments = case.assignments.all()
    upload_form = DocumentUploadForm()
    
    # Get all stages for the case's workflow
    all_stages = None
    if case.workflow and case.current_stage: # Check both exist
        all_stages = case.workflow.stages.all()
        # --- Calculate next_stage HERE ---
        current_order = case.current_stage.order
        next_stage = all_stages.filter(order=current_order + 1).first()


    context = {
        'case': case,
        'documents': documents,
        'assignments': assignments,
        'upload_form': upload_form,
        'all_stages': all_stages,
        'next_stage': next_stage,
    }
    return render(request, 'cases/case_detail.html', context)

# --- View 4: Document Audit Log (SECURED) ---
@login_required
def document_view_and_log(request, doc_pk):
    doc = get_object_or_404(Document, pk=doc_pk)
    case = doc.case # Get the case this document belongs to

    # --- Security Check ---
    is_admin = request.user.roles.filter(name='Admin').exists()
    is_assigned = CaseAssignment.objects.filter(case=case, user=request.user).exists()
    
    if not (is_admin or is_assigned):
        # If not an admin and not assigned, forbid access
        messages.error(request, "You do not have permission to view that document.")
        return redirect('users:dashboard') # Send to their dashboard
    
    # --- If security passes, log the action ---
    DocumentLog.objects.create(
        document=doc,
        user=request.user,
        action="Viewed"
    )
    
    # And redirect to the file
    return redirect(doc.file_upload.url)

# --- View 5: Workflow List (Admin) ---
@login_required
@user_passes_test(is_admin)
def workflow_list_view(request):
    workflows = CaseWorkflow.objects.all()
    context = {
        'workflows': workflows
    }
    return render(request, 'cases/workflow_list.html', context)

# --- View 6: Workflow Create (Admin) ---
@login_required
@user_passes_test(is_admin)
def workflow_create_view(request):
    if request.method == 'POST':
        form = WorkflowCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New workflow created successfully.")
            return redirect('cases:workflow-list')
    else:
        form = WorkflowCreateForm()
    
    context = {
        'form': form
    }
    return render(request, 'cases/workflow_create.html', context)

# --- View 7: Workflow Detail (Admin) ---
@login_required
@user_passes_test(is_admin)
def workflow_detail_view(request, pk):
    # Get the parent workflow
    workflow = get_object_or_404(CaseWorkflow, pk=pk)
    
    # Get all stages for this workflow, which are already ordered
    # thanks to the 'ordering' Meta option in the model
    stages = workflow.stages.all()
    
    context = {
        'workflow': workflow,
        'stages': stages
    }
    return render(request, 'cases/workflow_detail.html', context)

# --- View 8: Stage Create (Admin) ---
@login_required
@user_passes_test(is_admin)
def stage_create_view(request, workflow_pk):
    # Get the parent workflow this stage will belong to
    workflow = get_object_or_404(CaseWorkflow, pk=workflow_pk)
    
    if request.method == 'POST':
        form = StageCreateForm(request.POST)
        if form.is_valid():
            # Create the stage in memory
            stage = form.save(commit=False)
            # Assign it to the correct parent workflow
            stage.workflow = workflow
            stage.save()
            
            messages.success(request, f"New stage '{stage.name}' added to workflow.")
            # Redirect back to the detail page for that workflow
            return redirect('cases:workflow-detail', pk=workflow.pk)
    else:
        form = StageCreateForm()
        
    context = {
        'form': form,
        'workflow': workflow
    }
    return render(request, 'cases/stage_create.html', context)

# --- View 9: Advance Case Stage (NEW) ---
@login_required
@user_is_assigned_to_case
def advance_stage_view(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)
    
    # --- Security: Only Attorneys or Admins can advance a stage ---
    is_admin = request.user.roles.filter(name='Admin').exists()
    is_attorney = request.user.roles.filter(name='Attorney').exists()
    
    if not (is_admin or is_attorney):
        messages.error(request, "Only attorneys can advance a case stage.")
        return redirect('cases:case-detail', pk=case.pk)

    # --- Main Logic ---
    if not case.workflow or not case.current_stage:
        messages.error(request, "This case has no workflow to advance.")
        return redirect('cases:case-detail', pk=case.pk)

    current_order = case.current_stage.order
    
    # Find the next stage in the sequence
    next_stage = case.workflow.stages.filter(order=current_order + 1).first()
    
    if next_stage:
        now = timezone.now()
        
        # 1. Find the current, active log entry (it has no 'completed' timestamp)
        current_log_entry = CaseStageLog.objects.filter(
            case=case, 
            stage=current_stage,
            timestamp_completed__isnull=True
        ).first()
        
        # 2. Mark the current log entry as completed
        if current_log_entry:
            current_log_entry.timestamp_completed = now
            current_log_entry.save()
            
        # 3. Update the case's current stage
        case.current_stage = next_stage
        case.save()
        
        # 4. Create a NEW log entry for the stage we are entering
        CaseStageLog.objects.create(case=case, stage=next_stage, timestamp_entered=now)
        
        messages.success(request, f"Case stage advanced to: {next_stage.name}")
    else:
        # This was the last stage
        messages.info(request, "This case is already in its final stage.")
        
    # Redirect back to the detail page
    return redirect('cases:case-detail', pk=case.pk)

# --- View 10: Template List (Admin) ---
@login_required
def template_list_view(request):
    templates = Template.objects.all().order_by('name')

    # Discover any contract templates placed under the project's
    # `templates/cases/` directory that end with `_contract.html`.
    contract_files = []
    templates_dir = os.path.join(settings.BASE_DIR, 'templates', 'cases')
    if os.path.isdir(templates_dir):
        for fn in sorted(os.listdir(templates_dir)):
            # include both English and Spanish variants (e.g. _contract.html and _contract_es.html)
            if fn.endswith('_contract.html') or fn.endswith('_contract_es.html'):
                contract_files.append(fn)

    # Build prettier labels server-side to avoid using template filters
    contract_choices = []
    for fn in contract_files:
        # remove suffix and replace underscores with spaces, title-case
        label = fn.replace('_contract.html', '').replace('_', ' ').title()
        contract_choices.append((fn, label))

    context = {
        'templates': templates,
        # a list like ["vehicle_PurchaseandSale_contract.html", ...]
        'contract_files': contract_files,
        # choices list of (filename, pretty label) for template rendering
        'contract_choices': contract_choices,
        # json-encoded version to inject safely into JS
        'contract_files_json': json.dumps(contract_files),
        # lightweight placeholder map for client-side autofill (no case context here)
        'placeholder_map_json': json.dumps({})
    }
    return render(request, 'cases/template_list.html', context)


@login_required
def contract_template_view(request):
    """Return the raw HTML of a contract template located under
    `templates/cases/` given a `file` GET parameter. This endpoint
    validates the filename to avoid path traversal and ensures only
    files ending with `_contract.html` are returned.
    """
    file_name = request.GET.get('file')
    if not file_name or '/' in file_name or '..' in file_name:
        return JsonResponse({'error': 'Invalid file parameter.'}, status=400)

    # Allow both English and Spanish contract filenames. Accepted patterns:
    # - something_contract.html
    # - something_contract_es.html
    import re
    if not re.search(r'_contract(_es)?\.html$', file_name, re.IGNORECASE):
        return JsonResponse({'error': 'Not a contract template.'}, status=400)

    templates_dir = os.path.join(settings.BASE_DIR, 'templates', 'cases')
    file_path = os.path.join(templates_dir, file_name)
    # Ensure the resolved path is actually inside the templates_dir
    try:
        real_templates_dir = os.path.realpath(templates_dir)
        real_file_path = os.path.realpath(file_path)
    except Exception:
        return JsonResponse({'error': 'Invalid path resolution.'}, status=400)

    if not real_file_path.startswith(real_templates_dir):
        return JsonResponse({'error': 'Invalid file path.'}, status=400)

    if not os.path.exists(real_file_path):
        return JsonResponse({'error': 'File not found.'}, status=404)

    try:
        with open(real_file_path, 'r', encoding='utf-8') as fh:
            content = fh.read()
    except Exception:
        return JsonResponse({'error': 'Unable to read file.'}, status=500)

    return HttpResponse(content, content_type='text/html')

# --- View 11: Template Upload (Admin) ---
@login_required
@user_passes_test(is_admin)
def template_upload_view(request):
    if request.method == 'POST':
        form = TemplateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            template = form.save(commit=False)
            template.uploaded_by = request.user
            template.save()
            messages.success(request, f"Template '{template.name}' uploaded successfully.")
            return redirect('cases:template-list')
    else:
        form = TemplateUploadForm()
    
    context = {
        'form': form
    }
    return render(request, 'cases/template_upload.html', context)

# ---
# --- STEP 19: DOCUMENT GENERATION VIEW (UPGRADED)
# ---
@login_required
@user_is_assigned_to_case
def generate_document_view(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)

    templates = Template.objects.filter(
        models.Q(is_public=True) | models.Q(uploaded_by=request.user)
    ).distinct()

    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        if not template_id:
            messages.error(request, "Please select a template.")
        else:
            template = get_object_or_404(Template, pk=template_id)

            # --- 1. Build the Context ---
            # This matches placeholders to real data
            context = {}

            # Find the client
            client_assignment = case.assignments.filter(user__roles__name='Client').first()
            if client_assignment:
                context['client_name'] = client_assignment.user.get_full_name()
                context['client_email'] = client_assignment.user.email

            # Find the attorney
            attorney_assignment = case.assignments.filter(user__roles__name='Attorney').first()
            if attorney_assignment:
                context['attorney_name'] = attorney_assignment.user.get_full_name()

            context['case_title'] = case.case_title
            context['case_description'] = case.description

            # You can add any other fields from your Template.context_fields here
            # For example, if you stored {"client_address": "..."} in the case model.

            # --- 2. Generate the .docx Document ---
            try:
                # Open the template file (.docx)
                doc = DocxDocument(template.template_file.open())

                # Run our find-and-replace function
                doc = docx_find_and_replace(doc, context)

                # --- 3. Save the new file in memory ---
                file_buffer = io.BytesIO()
                doc.save(file_buffer)

                # Create a new file name
                file_name = f"Generated_{template.name.replace(' ', '_')}.docx"

                # Get the file content from the buffer
                file_content = file_buffer.getvalue()

                # --- 4. Save the new Document to the Case ---
                new_doc = Document.objects.create(
                    case=case,
                    title=f"Generated: {template.name}",
                    uploaded_by=request.user,
                    # Create a Django ContentFile from the buffer
                    file_upload=ContentFile(file_content, name=file_name)
                )

                # 5. Log the creation
                DocumentLog.objects.create(document=new_doc, user=request.user, action="Generated")

                messages.success(request, f"Document '{new_doc.title}' generated successfully.")
                return redirect('cases:case-detail', pk=case.pk)

            except Exception as e:
                print(f"!!! Error generating document: {e}")
                messages.error(request, f"Error generating document. Is the template file a valid .docx? Error: {e}")

    # Discover any HTML contract templates placed under the project's
    # `templates/cases/` directory that end with `_contract.html`.
    templates_dir = os.path.join(settings.BASE_DIR, 'templates', 'cases')
    contract_files = []
    if os.path.isdir(templates_dir):
        for fn in sorted(os.listdir(templates_dir)):
            # include both English and Spanish variants (e.g. _contract.html and _contract_es.html)
            if fn.endswith('_contract.html') or fn.endswith('_contract_es.html'):
                contract_files.append(fn)

    context = {
        'case': case,
        'templates': templates,
        'contract_files': contract_files,
        'contract_files_json': json.dumps(contract_files)
    }
    # Build a small, opinionated placeholder mapping so the frontend can autofill common keys
    placeholder_map = {}
    # Client and attorney
    if client_assignment:
        placeholder_map.update({
            'CLIENT': client_assignment.user.get_full_name(),
            'CLIENT_NAME': client_assignment.user.get_full_name(),
            'CLIENT_EMAIL': client_assignment.user.email or ''
        })
    if attorney_assignment:
        placeholder_map.update({
            'ATTORNEY': attorney_assignment.user.get_full_name(),
            'ATTORNEY_NAME': attorney_assignment.user.get_full_name()
        })

    # Case-related
    placeholder_map.update({
        'CASE_TITLE': case.case_title or '',
        'CASE_DESCRIPTION': case.description or ''
    })

    # Date/time defaults
    now = timezone.now()
    try:
        month_name = now.strftime('%B')
    except Exception:
        month_name = ''
    placeholder_map.update({
        'DAY': str(now.day),
        'MONTH': month_name,
        'YEAR': str(now.year),
        'TIME': now.strftime('%H:%M')
    })

    # Helpful aliases for common roles found in templates
    # Map a few role-like placeholders to the client (best-effort)
    if client_assignment:
        placeholder_map.setdefault('LESSOR', client_assignment.user.get_full_name())
        placeholder_map.setdefault('LESSEE', client_assignment.user.get_full_name())
        placeholder_map.setdefault('SELLER', client_assignment.user.get_full_name())
        placeholder_map.setdefault('BUYERS', client_assignment.user.get_full_name())

    context['placeholder_map_json'] = json.dumps(placeholder_map)
    # Provide case participants for role dropdowns (id + display name)
    participants = []
    for a in case.assignments.select_related('user').all():
        participants.append({'id': a.user.pk, 'name': a.user.get_full_name() or a.user.username})
    context['participants_json'] = json.dumps(participants)
    return render(request, 'cases/generate_document.html', context)

# --- View 12: Signature Request Page (Attorney-facing) ---
@login_required
def signature_request_view(request, doc_pk):
    doc = get_object_or_404(Document, pk=doc_pk)
    case = doc.case

    # --- Security & Permission Check ---
    is_admin = request.user.roles.filter(name='Admin').exists()
    is_assigned = CaseAssignment.objects.filter(case=case, user=request.user).exists()
    
    if not (is_admin or is_assigned):
        messages.error(request, "You do not have permission to access this.")
        return redirect('users:dashboard')

    is_attorney = request.user.roles.filter(name='Attorney').exists()
    if not (is_admin or is_attorney):
        messages.error(request, "Only attorneys can send signature requests.")
        return redirect('cases:case-detail', pk=case.pk)

    # --- Handle Form POST ---
    if request.method == 'POST':
        signer_id = request.POST.get('user_id')
        if not signer_id:
            messages.error(request, "Please select a user to send the request to.")
        else:
            signer = get_object_or_404(User, pk=signer_id)
            
            # Create the SignatureRequest
            sig_request = SignatureRequest.objects.create(
                document=doc,
                signer=signer,
                requested_by=request.user,
                status=SignatureRequest.Status.PENDING
            )
            
            # Build the secure signing link
            sign_link = request.build_absolute_uri(
                reverse('cases:signing-page', kwargs={'token': sig_request.token})
            )
            
            # TODO: Email this link. For now, we'll show it to the attorney.
            messages.success(request, f"Signature request sent to {signer.username}.")
            messages.info(request, f"Signing Link (for demo): {sign_link}")
            return redirect('cases:case-detail', pk=case.pk)

    # --- Handle GET ---
    potential_signers = case.assignments.exclude(user=request.user)
    context = {
        'doc': doc,
        'case': case,
        'potential_signers': potential_signers,
    }
    return render(request, 'cases/signature_request.html', context)


# --- View 13: Signing Page (Client-facing) ---
@login_required
def signing_page_view(request, token):
    # Find the request by its secure token
    sig_request = get_object_or_404(SignatureRequest, token=token)
    doc = sig_request.document

    # --- Security & Validation Checks ---
    # 1. Check if user is the correct signer
    if request.user != sig_request.signer:
        messages.error(request, "You are not authorized to sign this document.")
        return redirect('users:dashboard')
    
    # 2. Check if it's still pending
    if sig_request.status != SignatureRequest.Status.PENDING:
        messages.warning(request, "This document has already been signed or the request was cancelled.")
        return redirect('cases:case-detail', pk=doc.case.pk)

    # --- Handle the POST (signing) action ---
    if request.method == 'POST':
        # Check if the "agree" box was ticked
        if 'agree' not in request.POST:
            messages.error(request, "You must agree to the terms to sign.")
        else:
            # --- SUCCESS ---
            # 1. Update the request
            sig_request.status = SignatureRequest.Status.SIGNED
            sig_request.signed_at = timezone.now()
            sig_request.save()
            
            # 2. Create the permanent audit log
            DocumentLog.objects.create(
                document=doc,
                user=request.user,
                action="Signed",
                details=f"Signed via e-signature workflow."
            )
            
            messages.success(request, "Document successfully signed.")
            return redirect('cases:case-detail', pk=doc.case.pk)

    # --- Handle GET ---
    context = {
        'doc': doc,
        'sig_request': sig_request
    }
    return render(request, 'cases/signing_page.html', context)


