from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from .models import Notification
from .serializers import NotificationSerializer


class MyNotificationsView(APIView):
    """GET /notifications/me — UC-11."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user).order_by("-created_date")
        return Response({"data": NotificationSerializer(notifications, many=True).data})


class NotificationReadView(APIView):
    """PATCH /notifications/{id}/read."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.status = "READ"
        notification.save()
        return Response(NotificationSerializer(notification).data)
