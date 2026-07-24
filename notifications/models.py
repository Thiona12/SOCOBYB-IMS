from django.db import models
from django.conf import settings


class Notification(models.Model):
    CHANNEL_CHOICES = [("IN_APP", "In-app"), ("SMS", "SMS"), ("EMAIL", "Email"), ("WHATSAPP", "WhatsApp")]
    STATUS_CHOICES = [("UNREAD", "Unread"), ("READ", "Read")]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=150)
    message = models.TextField()
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="IN_APP")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="UNREAD")
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
