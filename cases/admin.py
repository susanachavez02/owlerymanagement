from django.contrib import admin

# Register your models here.
from .models import (
    Case, CaseAssignment, Document, DocumentLog,
    CaseWorkflow, CaseStage, Template, 
    SignatureRequest, CaseStageLog, Meeting, DocumentDueDate
)

# Register your models here.
admin.site.register(Case)
admin.site.register(CaseAssignment)
admin.site.register(Document)
admin.site.register(DocumentLog)
admin.site.register(CaseWorkflow)
admin.site.register(CaseStage)
admin.site.register(Template)
admin.site.register(SignatureRequest)
admin.site.register(CaseStageLog)
admin.site.register(Meeting)
admin.site.register(DocumentDueDate)