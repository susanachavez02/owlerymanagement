from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
from .models import Message
from .forms import NewMessageForm
from cases.models import Case, CaseAssignment # Need to import Case/Assignment
from cases.models import Case
from users.models import Role
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from cases.decorators import user_is_assigned_to_case
from django.core.mail import send_mail
from django.shortcuts import render, redirect

# --- View 1: Case Messaging Thread ---

@login_required
@user_is_assigned_to_case
def case_messaging_view(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)

    if request.method == "POST":
        form = NewMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.case = case
            msg.sender = request.user
            msg.sent_at = timezone.now()

            other_users = case.assignments.exclude(user=request.user)
            msg.recipient = other_users.first().user if other_users.exists() else request.user

            msg.save()
            messages.success(request, "Message sent.")

            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect("cases:case-detail", pk=case.pk)

    # GET fallback (you can keep this page, but you won’t be forced into it anymore)
    form = NewMessageForm()
    messages_thread = Message.objects.filter(case=case).filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by("sent_at")

    return render(request, "communication/case_messaging.html", {
        "case": case,
        "messages_thread": messages_thread,
        "form": form,
    })

@login_required # Good practice to ensure user is logged in
def send_case_notification(request, case_id):
    """
    Handles the POST request from the email notification form
    on the case detail page.
    """
    
    # Get the case object so we can use its info
    case = get_object_or_404(Case, pk=case_id)
    
    if request.method == 'POST':
        # 1. Get all the data from the form
        recipient_email = request.POST.get('recipient_email')
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')
        
        # 2. Get the sender's info (the logged-in attorney/admin)
        sender = request.user
        
        # 3. Create a more detailed email message
        full_message = f"""
        You have received a notification regarding Case: {case.case_title}

        From: {sender.get_full_name()} ({sender.email})
        
        -----------------
        {message_body}
        -----------------
        
        This is an automated message from the Owlery Portal.
        """
        
        try:
            # 4. Try to send the email
            send_mail(
                subject,                            # The subject from the form
                full_message,                       # The detailed message body
                settings.DEFAULT_FROM_EMAIL,           # The 'from' email (from settings.py)
                [recipient_email],                  # List of recipients
                fail_silently=False,
            )
            
            # 5. Add a success message
            messages.success(request, 'Your email notification has been sent successfully!')

        except Exception as e:
            # 6. If it fails, add an error message
            messages.error(request, f'Error sending email: {e}')
            
        # 7. Redirect back to the case detail page
        return redirect('cases:case-detail', pk=case.id)
    
    # If not POST, just redirect back (this view shouldn't be accessed via GET)
    return redirect('cases:case-detail', pk=case.id)