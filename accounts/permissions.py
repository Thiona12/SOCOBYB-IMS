"""
Custom DRF permission class implementing D-08's hybrid model as a reusable
decorator-style class, mirroring requirePermission() from the Express version.
Usage: permission_classes = [HasPermission("PRODUCT_CREATE")]
"""
from rest_framework.permissions import BasePermission


def HasPermission(code):
    class _HasPermission(BasePermission):
        message = f"Missing permission: {code}"

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.has_perm_code(code))

    return _HasPermission
