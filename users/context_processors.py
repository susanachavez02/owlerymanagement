def user_roles_processor(request):
    """Adds the user's role names to the template context."""
    roles = []
    if request.user.is_authenticated:
        # Get the names of all roles assigned to the user
        roles = list(request.user.roles.values_list('name', flat=True))

    return {
        'user_roles': roles,
        'is_admin_user': 'Admin' in roles # Add a simple boolean flag
    }