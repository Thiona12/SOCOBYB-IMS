"""
Permission-gated stub endpoints for D-12 route groups not yet implemented.
Each mirrors stubs.routes.js from the earlier Express scaffold: correct method,
path, and permission check, returning 501 until the real service logic is
written. The business rule each one must enforce is noted in the comment.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasPermission


def make_stub(permission_code=None, note=""):
    class _Stub(APIView):
        permission_classes = [IsAuthenticated] if not permission_code else [HasPermission(permission_code)]

        def get(self, request, *a, **kw):
            return self._not_implemented()

        def post(self, request, *a, **kw):
            return self._not_implemented()

        def patch(self, request, *a, **kw):
            return self._not_implemented()

        def delete(self, request, *a, **kw):
            return self._not_implemented()

        def _not_implemented(self):
            return Response(
                {"error": {"code": "NOT_IMPLEMENTED", "message": f"Scaffold only. {note}"}},
                status=501,
            )
    return _Stub.as_view()
