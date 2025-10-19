from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# --- NEW MODEL: CaseWorkflow ---
class CaseWorkflow(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., 'Litigation', 'Contract Review'")

    def __str__(self):
        return self.name

# --- NEW MODEL: CaseStage ---
class CaseStage(models.Model):
    workflow = models.ForeignKey(CaseWorkflow, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=100, help_text="e.g., 'Discovery', 'Negotiation'")
    order = models.PositiveIntegerField(help_text="The step number (1, 2, 3...)")

    class Meta:
        # Ensures that 'order' is unique FOR EACH workflow
        unique_together = ('workflow', 'order')
        # Sorts stages by their order number by default
        ordering = ['order']

    def __str__(self):
        return f"{self.workflow.name} - Step {self.order}: {self.name}"

# --- UPDATED MODEL: Case ---
class Case(models.Model):
    case_title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    date_filed = models.DateField(auto_now_add=True, help_text="Date the case was created in the system.")
    is_archived = models.BooleanField(default=False)
    
    # --- ADD THESE TWO LINES ---
    workflow = models.ForeignKey(CaseWorkflow, on_delete=models.SET_NULL, null=True, blank=True, related_name='cases')
    current_stage = models.ForeignKey(CaseStage, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_cases')

    def __str__(self):
        return self.case_title

# Model 2: CaseAssignment - links User to a Case
class CaseAssignment(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='case_assignments')
    
    # This field isn't in the MVP but is good practice if you want to know *why*
    # a user is assigned (e.g., as 'Lead Attorney', 'Client', 'Paralegal')
    # For the MVP, we can just rely on the user's main 'Role'
    
    class Meta:
        # Prevents a user from being assigned to the same case twice
        unique_together = ('case', 'user')

    def __str__(self):
        return f"{self.user.username} assigned to {self.case.case_title}"

# Model 3: Document
class Document(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file_upload = models.FileField(upload_to='case_documents/%Y/%m/%d/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    version_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.title} (Case: {self.case.case_title})"

# Model 4: DocumentLog
class DocumentLog(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # e.g., 'Uploaded', 'Viewed', 'Signed', 'Edited'
    action = models.CharField(max_length=50)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.action} on {self.document.title} by {self.user.username}"
    
