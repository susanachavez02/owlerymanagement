from django import forms
from django.contrib.auth.models import User
from .models import Case, Document, CaseWorkflow, CaseStage         # From the current 'cases' app
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