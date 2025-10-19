from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
# We need to import the admin test function from our 'users' app

# --- Model Imports ---
from .models import (
    Case, CaseAssignment, Document, DocumentLog,
    CaseWorkflow, CaseStage, TimeEntry, Template, SignatureRequest
)
# --- Form Imports ---
from .forms import (
    CaseCreateForm, DocumentUploadForm,
    WorkflowCreateForm, StageCreateForm, TimeEntryForm, TemplateUploadForm
)

from users.views import is_admin
from .decorators import user_is_assigned_to_case

# --- Django's File handling utilities ---
from django.core.files.base import ContentFile

# --- View 1: Case List (Admin) ---

@login_required
@user_passes_test(is_admin)
def case_list_view(request):
    # Get all cases, ordered by the most recently filed
    cases = Case.objects.all().order_by('-date_filed')
    
    # Pass the list of cases into the template
    context = {
        'cases': cases
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
        
        # Check if the 'log_time' button was pressed
        elif 'log_time' in request.POST:
            time_form = TimeEntryForm(request.POST)
            if time_form.is_valid():
                entry = time_form.save(commit=False)
                entry.case = case
                entry.attorney = request.user
                entry.save()
                messages.success(request, "Time entry logged successfully.")
                return redirect('cases:case-detail', pk=case.pk)
    
    # --- GET Request Logic ---
    documents = case.documents.all().order_by('-id')
    assignments = case.assignments.all()
    upload_form = DocumentUploadForm() 
    
    # Get all stages for the case's workflow
    all_stages = None
    if case.workflow:
        all_stages = case.workflow.stages.all()

    # --- NEW: Get time entries ---
    time_entries = case.time_entries.all().order_by('-date')
    time_form = TimeEntryForm()
    # --- END NEW ---

    context = {
        'case': case,
        'documents': documents,
        'assignments': assignments,
        'upload_form': upload_form,
        'all_stages': all_stages,
        'time_entries': time_entries, # <-- Add to context
        'time_form': time_form,       # <-- Add to context
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
        # We found a next stage, so update the case
        case.current_stage = next_stage
        case.save()
        messages.success(request, f"Case stage advanced to: {next_stage.name}")
    else:
        # This was the last stage
        messages.info(request, "This case is already in its final stage.")
        
    # Redirect back to the detail page
    return redirect('cases:case-detail', pk=case.pk)

# --- View 10: Template List (Admin) ---
@login_required
@user_passes_test(is_admin)
def template_list_view(request):
    templates = Template.objects.all().order_by('name')
    context = {
        'templates': templates
    }
    return render(request, 'cases/template_list.html', context)

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

# --- STEP 19: DOCUMENT GENERATION VIEW
# ---
@login_required
@user_is_assigned_to_case
def generate_document_view(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)
    
    # Get all available templates (public ones or ones uploaded by this user)
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
            # This is where we match the template's fields to the case data.
            context = {}
            
            # Find the client on the case
            client_assignment = case.assignments.filter(user__roles__name='Client').first()
            if client_assignment:
                context['client_name'] = client_assignment.user.get_full_name()
                context['client_email'] = client_assignment.user.email
            
            # Find the attorney on the case
            attorney_assignment = case.assignments.filter(user__roles__name='Attorney').first()
            if attorney_assignment:
                context['attorney_name'] = attorney_assignment.user.get_full_name()

            context['case_title'] = case.case_title
            context['case_description'] = case.description
            
            # --- 2. Generate the (Placeholder) Document ---
            # This is a simple placeholder. We are NOT using the .docx file yet.
            # We just create a .txt file with the context data to prove it works.
            
            file_content = f"--- GENERATED DOCUMENT ---\n"
            file_content += f"Template Used: {template.name}\n"
            file_content += "----------------------------\n\n"
            
            for key, value in context.items():
                file_content += f"{key}: {value}\n"
            
            file_name = f"{case.case_title.replace(' ', '_')}_{template.name.replace(' ', '_')}.txt"
            
            # --- 3. Save the new Document ---
            new_doc = Document.objects.create(
                case=case,
                title=f"Generated: {template.name}",
                uploaded_by=request.user,
                # We save the file content to the FileField
                file_upload=ContentFile(file_content.encode('utf-8'), name=file_name)
            )
            
            # 4. Log the creation
            DocumentLog.objects.create(document=new_doc, user=request.user, action="Generated")
            
            messages.success(request, f"Document '{new_doc.title}' generated successfully.")
            return redirect('cases:case-detail', pk=case.pk)

    context = {
        'case': case,
        'templates': templates
    }
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