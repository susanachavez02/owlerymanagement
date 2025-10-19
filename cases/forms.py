from django import forms
from django.contrib.auth.models import User
from .models import (
    Case, Document, CaseWorkflow, CaseStage,
    TimeEntry, Template, Invoice
)
from users.models import Role   # From the 'users' app

class CaseCreateForm(forms.ModelForm):
    # We need to manually add fields to select the users
    
    # Find all users who have the 'Attorney' role
    attorney = forms.ModelChoiceField(
        queryset=User.objects.filter(roles__name='Attorney'),
        label="Assign Attorney"
    )
    
    # Find all users who have the 'Client' role
    client = forms.ModelChoiceField(
        queryset=User.objects.filter(roles__name='Client'),
        label="Assign Client"
    )

    class Meta:
        model = Case
        # These are the fields from the Case model we want in the form
        fields = ['case_title', 'description', 'workflow']

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        # We only want the user to provide these two fields
        fields = ['title', 'file_upload']

# --- NEW: Workflow Form ---
class WorkflowCreateForm(forms.ModelForm):
    class Meta:
        model = CaseWorkflow
        fields = ['name']

# --- NEW: Stage Form ---
class StageCreateForm(forms.ModelForm):
    class Meta:
        model = CaseStage
        fields = ['name', 'order']
        widgets = {
            'order': forms.NumberInput(attrs={'min': 1})
        }

class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['date', 'hours', 'description', 'is_billable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'hours': forms.NumberInput(attrs={'step': '0.25', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set 'is_billable' to True by default
        self.fields['is_billable'].initial = True

class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = ['name', 'template_file', 'is_public', 'context_fields']
        help_texts = {
            'context_fields': 'Enter as a JSON list, e.g., ["client_name", "case_title"]'
        }

# --- NEW: Invoice Creation Form ---
class InvoiceCreateForm(forms.ModelForm):
    # This field will show a list of unbilled time entries
    time_entries = forms.ModelMultipleChoiceField(
        queryset=TimeEntry.objects.none(), # We'll set this in the view
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    class Meta:
        model = Invoice
        fields = ['due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # We must pass the case 'pk' from the view to filter time_entries
        case_pk = kwargs.pop('case_pk', None)
        super().__init__(*args, **kwargs)
        
        if case_pk:
            # This is the magic:
            # We filter for TimeEntry objects that belong to this case
            # AND do not have an invoice_item linked to them (isnull=True)
            self.fields['time_entries'].queryset = TimeEntry.objects.filter(
                case__pk=case_pk,
                invoice_item__isnull=True,
                is_billable=True
            )