from django import forms
from django.contrib.auth.models import User
from .models import (
    Case, Document, CaseWorkflow, CaseStage,
    TimeEntry, Template
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