from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
import uuid

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
    
class TimeEntry(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='time_entries')
    # Link to the main User model (which represents the attorney)
    attorney = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_entries')
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    is_billable = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.hours} hrs on {self.date} for {self.case.case_title}"
    
class Template(models.Model):
    name = models.CharField(max_length=255, help_text="e.g., 'Real Estate Closing Contract'")
    
    # The actual .docx or .pdf template file
    template_file = models.FileField(upload_to='document_templates/')
    
    # Is this template available to all attorneys or just the one who created it?
    is_public = models.BooleanField(default=False)
    
    # Stores a list of placeholder keys the template expects
    # e.g., ["client_name", "case_title", "attorney_name"]
    context_fields = models.JSONField(
        blank=True, 
        null=True, 
        help_text="JSON list of placeholder fields this template uses."
    )
    
    # Optional: Link to the attorney who uploaded it
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.name
    
# --- NEW: SignatureRequest Model ---
class SignatureRequest(models.Model):
    # Status choices
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SIGNED = 'SIGNED', 'Signed'
        REJECTED = 'REJECTED', 'Rejected'

    # Link to the document that needs signing
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signature_requests')
    
    # Link to the user who is asked to sign
    signer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='signature_requests_to_sign')
    
    # Link to the user who SENT the request
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='signature_requests_sent')

    # The current status of the request
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # A one-time-use, secure token for the signing link (optional but good)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Request for {self.signer.username} to sign {self.document.title} ({self.status})"
    
# --- NEW: Invoice Model ---
class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        PAID = 'PAID', 'Paid'
        VOID = 'VOID', 'Void'

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='invoices')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Invoice #{self.pk} for {self.case.case_title} - {self.status}"

# --- NEW: InvoiceItem Model ---
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    # Link to the billable time
    time_entry = models.OneToOneField(
        TimeEntry, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='invoice_item'
    )
    
    # In case of manual line items
    description = models.CharField(max_length=255)
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    rate = models.DecimalField(max_digits=7, decimal_places=2, help_text="Rate at the time of billing")
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Item for Invoice #{self.invoice.pk}: {self.description}"
    
# --- Case Stage Log Model ---
class CaseStageLog(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='stage_logs')
    stage = models.ForeignKey(CaseStage, on_delete=models.CASCADE, related_name='logs')
    
    # When the case entered this stage
    timestamp_entered = models.DateTimeField(default=timezone.now)
    
    # When the case left this stage (can be empty if it's the current stage)
    timestamp_completed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.case.case_title} in {self.stage.name} (Entered: {self.timestamp_entered})"

    @property
    def duration_in_stage(self):
        if self.timestamp_completed:
            return self.timestamp_completed - self.timestamp_entered
        # If not completed, return time elapsed so far
        return timezone.now() - self.timestamp_entered