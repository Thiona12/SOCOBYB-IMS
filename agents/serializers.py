from rest_framework import serializers
from .models import Agent, Assignment, AssignmentDetail


class AgentSerializer(serializers.ModelSerializer):
    outstanding_count = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = ["id", "name", "phone", "status", "credit_limit", "outstanding_count"]

    def get_outstanding_count(self, obj):
        return AssignmentDetail.objects.filter(assignment__agent=obj, payment_status="UNPAID").count()


class AssignmentCreateSerializer(serializers.Serializer):
    """POST /agents/{id}/assignments — BR-AGT-002/003."""
    stockItemIds = serializers.ListField(child=serializers.IntegerField())
