from django import forms
from django.contrib.auth.models import User
from .models import (
    Case, Document, CaseWorkflow, CaseStage, Template, Meeting, Case, ConsultationRequest
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

class CaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ["case_title", "description", "notes", "current_stage"]  # adjust to your model
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

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

class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = ['name', 'template_file', 'is_public', 'context_fields']
        help_texts = {
            'context_fields': 'Enter as a JSON list, e.g., ["client_name", "case_title"]'
        }

# --- Meeting Form  ---
class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['case', 'title', 'meeting_type', 'scheduled_time', 'duration_minutes', 'description', 'participants']
        widgets = {
            'case': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Client Check-in'}),
            'meeting_type': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'text'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '15', 'step': '15'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'participants': forms.CheckboxSelectMultiple(),
        }

class ConsultationScheduleForm(forms.Form):
    MEETING_TYPES = (
        ('Online Video', 'Online Video (Zoom/Teams)'),
        ('Phone Call', 'Phone Call'),
        ('In Person', 'In Person at Office'),
    )
    
    meeting_type = forms.ChoiceField(choices=MEETING_TYPES, label="Meeting Type")
    
    scheduled_time = forms.DateTimeField(
        required=False, 
        label="Set Specific Time",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        help_text="Select a confirmed time..."
    )
    
    booking_link = forms.URLField(
        required=False, 
        label="OR Send Booking Link",
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://calendly.com/...'}),
        help_text="...or provide a link for them to choose."
    )
    
    additional_message = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        label="Message to Client"
    )

    def clean(self):
        cleaned_data = super().clean()
        time = cleaned_data.get("scheduled_time")
        link = cleaned_data.get("booking_link")

        if not time and not link:
            raise forms.ValidationError("Please either set a specific time OR provide a booking link.")
        return cleaned_data
    

# Add this to the bottom of cases/forms.py

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = ConsultationRequest
        fields = ['name', 'phone', 'email', 'service_needed', 'attorney']
        widgets = {
            'service_needed': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'attorney': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter the attorney dropdown to only show users with the 'Attorney' role
        self.fields['attorney'].queryset = User.objects.filter(roles__name='Attorney')
        self.fields['attorney'].empty_label = "Select an Attorney (Optional)"


class CaseReassignForm(forms.Form):
    new_attorney = forms.ModelChoiceField(
        queryset=User.objects.none(),
        empty_label="Select an attorney...",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, attorney_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if attorney_qs is not None:
            self.fields["new_attorney"].queryset = attorney_qs