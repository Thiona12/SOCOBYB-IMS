"""Enforces D-08's permission model in the webapp views the same way
accounts/permissions.py (HasPermission) does for the DRF API — the gap
being fixed here is that webapp views previously only checked login_required,
so ANY logged-in staff member could reach ANY staff page regardless of their
actual role/permissions."""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect


def require_permission(code):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not request.user.has_perm_code(code):
                messages.error(request, f"Accès refusé : permission '{code}' requise.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
