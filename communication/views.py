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
from cases.decorators import user_is_assigned_to_case
from django.core.mail import send_mail
from django.shortcuts import render, redirect

# --- View 1: Case Messaging Thread ---

@login_required
@user_is_assigned_to_case 
def case_messaging_view(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)
        
    # --- Handle New Message POST ---
    if request.method == 'POST':
        form = NewMessageForm(request.POST)
        if form.is_valid():
            # Create the message in memory
            msg = form.save(commit=False)
            msg.case = case
            msg.sender = request.user
            
            # --- Find the Recipient ---
            # Find all users on the case, EXCLUDING the sender
            other_users = case.assignments.exclude(user=request.user)
            
            # For the MVP, we assume there is only one other person
            # (e.g., Client messages Attorney, or Attorney messages Client)
            if other_users.exists():
                msg.recipient = other_users.first().user
            else:
                # Handle edge case (e.g., admin talking to themselves)
                msg.recipient = request.user 
            
            msg.save()
            messages.success(request, "Message sent.")
            return redirect('communication:case-messaging', case_pk=case.pk)
    
    # --- Handle GET Request ---
    # Create a blank form
    form = NewMessageForm()
    
    # Get all messages for this case where the user is either the sender OR recipient
    # This is so the user only sees their own conversations
    messages_thread = Message.objects.filter(
        case=case
    ).filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by('sent_at') # Show oldest first
    
    context = {
        'case': case,
        'messages_thread': messages_thread,
        'form': form,
    }
    
    return render(request, 'communication/case_messaging.html', context)



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