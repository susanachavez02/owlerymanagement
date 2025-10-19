from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Message
from .forms import NewMessageForm
from cases.models import Case, CaseAssignment # Need to import Case/Assignment
from users.models import Role
from cases.decorators import user_is_assigned_to_case

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