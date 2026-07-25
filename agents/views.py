from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from accounts.permissions import HasPermission
from inventory.models import StockItem
from .models import Agent, Assignment, AssignmentDetail
from .serializers import AgentSerializer, AssignmentCreateSerializer


class AgentListCreateView(APIView):
    """POST/GET /agents — UC-10, AGENT_APPROVE."""
    permission_classes = [HasPermission("AGENT_APPROVE")]

    def get(self, request):
        agents = Agent.objects.all()
        return Response({"data": AgentSerializer(agents, many=True).data})

    def post(self, request):
        serializer = AgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = serializer.save(status="PENDING")
        return Response(AgentSerializer(agent).data, status=201)


class AgentApproveView(APIView):
    permission_classes = [HasPermission("AGENT_APPROVE")]

    def patch(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        agent.status = "APPROVED"
        agent.save()
        return Response(AgentSerializer(agent).data)


class AgentAssignmentsView(APIView):
    """POST /agents/{id}/assignments — BR-AGT-002/003.
    Checks creditLimit - outstanding >= count(stockItemIds) BEFORE creating anything,
    returning 409 CREDIT_LIMIT_EXCEEDED if it would be violated (D-12 §12 sample)."""
    permission_classes = [HasPermission("AGENT_APPROVE")]

    @transaction.atomic
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stock_item_ids = serializer.validated_data["stockItemIds"]

        outstanding = AssignmentDetail.objects.filter(assignment__agent=agent, payment_status="UNPAID").count()
        requested = len(stock_item_ids)

        # BR-AGT-003: credit limit is a COUNT of unpaid devices here (not a currency amount),
        # matching D-03 §6's "plafond de crédit" as a device count ceiling.
        if outstanding + requested > agent.credit_limit:
            return Response(
                {"error": {
                    "code": "CREDIT_LIMIT_EXCEEDED",
                    "message": f"Agent has {outstanding} outstanding, limit is {agent.credit_limit}, "
                               f"cannot assign {requested} more",
                }},
                status=409,
            )

        stock_items = StockItem.objects.filter(id__in=stock_item_ids, status="AVAILABLE")
        if stock_items.count() != requested:
            return Response(
                {"error": {"code": "STOCK_INSUFFICIENT", "message": "One or more stock items are not available"}},
                status=409,
            )

        assignment = Assignment.objects.create(agent=agent, status="ACTIVE")
        for item in stock_items:
            item.status = "ASSIGNED"
            item.save()
            AssignmentDetail.objects.create(assignment=assignment, stock_item=item, payment_status="UNPAID")

        return Response({"assignmentId": assignment.id, "itemsAssigned": requested}, status=201)


class AssignmentDetailPayView(APIView):
    """PATCH /assignment-details/{id}/pay — BR-AGT-004: ASSIGNED -> SOLD."""
    permission_classes = [HasPermission("AGENT_APPROVE")]

    def patch(self, request, detail_id):
        detail = get_object_or_404(AssignmentDetail, id=detail_id)
        detail.payment_status = "PAID"
        detail.save()
        detail.stock_item.status = "SOLD"
        detail.stock_item.save()
        return Response({"assignmentDetailId": detail.id, "paymentStatus": "PAID", "stockItemStatus": "SOLD"})
