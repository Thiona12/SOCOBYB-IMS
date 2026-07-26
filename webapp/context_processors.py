"""Exposes the logged-in user's resolved permissions to every template,
so nav links only appear for what the user can actually access — fixes
the bug where every staff user saw an identical nav regardless of role."""

def user_permission_flags(request):
    if not request.user.is_authenticated:
        return {}
    perms = set(request.user.resolved_permissions()) if hasattr(request.user, "resolved_permissions") else set()
    return {
        "can_view_stock": "STOCK_VIEW" in perms,
        "can_create_transfer": "TRANSFER_CREATE" in perms,
        "can_approve_transfer": "TRANSFER_APPROVE" in perms,
        "can_manage_agents": "AGENT_APPROVE" in perms,
        "can_view_reports": "REPORT_VIEW" in perms,
    }
