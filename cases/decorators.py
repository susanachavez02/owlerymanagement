from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Case, CaseAssignment

def user_is_assigned_to_case(view_func):
    """
    Decorator to check if a user is an admin or is assigned to the case.
    This assumes the view's URL has a kwarg named 'pk' or 'case_pk'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Get the case's primary key from the URL
        case_pk = kwargs.get('pk') or kwargs.get('case_pk')
        
        if not case_pk:
            # This is a safety check in case we forgot to add the pk
            messages.error(request, "Error: Case ID not found.")
            return redirect('/') 
            
        case = get_object_or_404(Case, pk=case_pk)

        # --- The Security Check ---
        is_admin = request.user.roles.filter(name='Admin').exists()
        is_assigned = CaseAssignment.objects.filter(case=case, user=request.user).exists()

        if is_admin or is_assigned:
            # If they are an admin OR assigned, run the original view
            return view_func(request, *args, **kwargs)
        else:
            # Otherwise, forbid access
            messages.error(request, "You do not have permission to view that case.")
            return redirect('/') # Redirect to homepage
            
    return _wrapped_view