from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if hasattr(request.user, 'profile') and request.user.profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You are not authorized to access this page.")
            return redirect('home')
        return wrapper
    return decorator
