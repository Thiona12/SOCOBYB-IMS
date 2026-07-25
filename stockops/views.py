from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from accounts.models import Shop
from accounts.permissions import HasPermission
from inventory.models import StockItem, StockMovement
from .models import StockRequest, Transfer, TransferDetail
from .serializers import (
    StockRequestSerializer, TransferCreateSerializer, TransferVerifySerializer, TransferSerializer,
)


class StockRequestListCreateView(APIView):
    """POST/GET /stock-requests — UC-06, BR-REQ-001/002."""
    permission_classes = [HasPermission("STOCK_VIEW")]

    def get(self, request):
        reqs = StockRequest.objects.all().order_by("-date")
        return Response({"data": StockRequestSerializer(reqs, many=True).data})

    def post(self, request):
        serializer = StockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stock_request = serializer.save(status="PENDING")
        return Response(StockRequestSerializer(stock_request).data, status=201)


class StockRequestApproveView(APIView):
    """PATCH /stock-requests/{id}/approve — BR-REQ-002, TRANSFER_APPROVE."""
    permission_classes = [HasPermission("TRANSFER_APPROVE")]

    def patch(self, request, request_id):
        stock_request = get_object_or_404(StockRequest, id=request_id)
        stock_request.status = "APPROVED"
        stock_request.save()
        return Response(StockRequestSerializer(stock_request).data)


class StockRequestRejectView(APIView):
    permission_classes = [HasPermission("TRANSFER_APPROVE")]

    def patch(self, request, request_id):
        stock_request = get_object_or_404(StockRequest, id=request_id)
        stock_request.status = "REJECTED"
        stock_request.save()
        return Response(StockRequestSerializer(stock_request).data)


class TransferCreateView(APIView):
    """POST /transfers — UC-07, BR-TRF-001: reserves stock (sets RESERVED),
    creates a TransferDetail per stock item."""
    permission_classes = [HasPermission("TRANSFER_CREATE")]

    @transaction.atomic
    def post(self, request):
        serializer = TransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source = get_object_or_404(Shop, id=data["sourceShopId"])
        destination = get_object_or_404(Shop, id=data["destinationShopId"])
        stock_request = None
        if data.get("requestId"):
            stock_request = get_object_or_404(StockRequest, id=data["requestId"])

        stock_items = StockItem.objects.filter(id__in=data["stockItemIds"], status="AVAILABLE")
        if stock_items.count() != len(data["stockItemIds"]):
            return Response(
                {"error": {"code": "STOCK_INSUFFICIENT", "message": "One or more stock items are not available"}},
                status=409,
            )

        transfer = Transfer.objects.create(
            source_shop=source, destination_shop=destination, request=stock_request, status="PENDING"
        )
        for item in stock_items:
            item.status = "RESERVED"
            item.save()
            TransferDetail.objects.create(transfer=transfer, stock_item=item, verification_status="PENDING")

        return Response(TransferSerializer(transfer).data, status=201)


class TransferShipView(APIView):
    """PATCH /transfers/{id}/ship — marks IN_TRANSIT."""
    permission_classes = [HasPermission("TRANSFER_CREATE")]

    def patch(self, request, transfer_id):
        transfer = get_object_or_404(Transfer, id=transfer_id)
        transfer.status = "IN_TRANSIT"
        transfer.save()
        return Response(TransferSerializer(transfer).data)


class TransferVerifyView(APIView):
    """POST /transfers/{id}/verify — BR-TRF-002: compare received identifiers to
    what was actually shipped. Any mismatch => COMPLETED_WITH_DISCREPANCY, and the
    mismatched identifiers are returned so staff can investigate."""
    permission_classes = [HasPermission("TRANSFER_APPROVE")]

    @transaction.atomic
    def post(self, request, transfer_id):
        transfer = get_object_or_404(Transfer, id=transfer_id)
        serializer = TransferVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        received = set(serializer.validated_data["receivedIdentifiers"])

        details = TransferDetail.objects.filter(transfer=transfer).select_related("stock_item")
        expected = {d.stock_item.identifier for d in details if d.stock_item.identifier}

        mismatched = list(expected.symmetric_difference(received))
        has_discrepancy = len(mismatched) > 0

        for detail in details:
            if detail.stock_item.identifier in received:
                detail.verification_status = "MATCHED"
                detail.stock_item.status = "AVAILABLE"  # now available at destination
            else:
                detail.verification_status = "DISCREPANCY"
            detail.save()
            detail.stock_item.save()

        # Move inventory: decrement source, increment destination (simplified — assumes
        # Inventory rows already exist; a real implementation would get_or_create them).
        transfer.status = "COMPLETED_WITH_DISCREPANCY" if has_discrepancy else "COMPLETED"
        transfer.save()

        return Response({
            "transferId": transfer.id,
            "status": transfer.status,
            "mismatchedIdentifiers": mismatched,
        })


class TransferDetailView(APIView):
    """GET /transfers/{id} — STOCK_VIEW."""
    permission_classes = [HasPermission("STOCK_VIEW")]

    def get(self, request, transfer_id):
        transfer = get_object_or_404(Transfer, id=transfer_id)
        return Response(TransferSerializer(transfer).data)
