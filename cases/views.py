from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

# We need to import the admin test function from our 'users' app

# --- Model Imports ---
from .models import (
    Case, CaseAssignment, Document, DocumentLog,
    CaseWorkflow, CaseStage, TimeEntry
)
# --- Form Imports ---
from .forms import (
    CaseCreateForm, DocumentUploadForm,
    WorkflowCreateForm, StageCreateForm, TimeEntryForm
)

from users.views import is_admin
from .decorators import user_is_assigned_to_case

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