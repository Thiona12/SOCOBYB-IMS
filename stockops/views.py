from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from accounts.models import Shop
from accounts.permissions import HasPermission
from catalog.models import Product
from inventory.models import StockItem, StockMovement, Inventory
from .models import StockRequest, Transfer, TransferDetail, TransferBulkDetail
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
    """POST /transfers — UC-07, BR-TRF-001: reserves stock at creation time.
    Tracked items: stock item status -> RESERVED (unchanged from before).
    Bulk items: source Inventory.quantity is decremented immediately (reserved),
    and only credited to the destination once verify() confirms receipt — this
    was the gap flagged in the README; now fixed."""
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

        stock_item_ids = data.get("stockItemIds", [])
        bulk_items = data.get("bulkItems", [])

        stock_items = StockItem.objects.filter(id__in=stock_item_ids, status="AVAILABLE")
        if stock_items.count() != len(stock_item_ids):
            return Response(
                {"error": {"code": "STOCK_INSUFFICIENT", "message": "One or more stock items are not available"}},
                status=409,
            )

        # Validate bulk availability BEFORE mutating anything.
        source_inventories = {}
        for bulk in bulk_items:
            inv = Inventory.objects.filter(shop=source, product_id=bulk["productId"]).first()
            if not inv or inv.quantity < bulk["quantity"]:
                return Response(
                    {"error": {"code": "STOCK_INSUFFICIENT",
                               "message": f"Not enough bulk stock for productId={bulk['productId']} at source shop"}},
                    status=409,
                )
            source_inventories[bulk["productId"]] = inv

        transfer = Transfer.objects.create(
            source_shop=source, destination_shop=destination, request=stock_request, status="PENDING"
        )

        for item in stock_items:
            item.status = "RESERVED"
            item.save()
            TransferDetail.objects.create(transfer=transfer, stock_item=item, verification_status="PENDING")

        for bulk in bulk_items:
            inv = source_inventories[bulk["productId"]]
            inv.quantity -= bulk["quantity"]  # reserved out of source immediately
            inv.save()
            TransferBulkDetail.objects.create(
                transfer=transfer, product_id=bulk["productId"],
                shipped_quantity=bulk["quantity"], verification_status="PENDING",
            )

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
    """POST /transfers/{id}/verify — BR-TRF-002: compare received identifiers/quantities to
    what was actually shipped. Any mismatch => COMPLETED_WITH_DISCREPANCY, and the specifics
    are returned so staff can investigate.

    Tracked items: identifier-by-identifier match (unchanged from before).
    Bulk items: received quantity is credited to the DESTINATION Inventory (get_or_create'd
    if this is the first time that product arrives at that shop) — this is the fix for the
    gap noted in the README; previously nothing happened to Inventory rows on verify."""
    permission_classes = [HasPermission("TRANSFER_APPROVE")]

    @transaction.atomic
    def post(self, request, transfer_id):
        transfer = get_object_or_404(Transfer, id=transfer_id)
        serializer = TransferVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        received_identifiers = set(serializer.validated_data.get("receivedIdentifiers", []))
        received_bulk = {b["productId"]: b["quantity"] for b in serializer.validated_data.get("receivedBulkItems", [])}

        has_discrepancy = False
        mismatched_identifiers = []
        bulk_discrepancies = []

        # ---- Tracked items ----
        details = TransferDetail.objects.filter(transfer=transfer).select_related("stock_item")
        expected_identifiers = {d.stock_item.identifier for d in details if d.stock_item.identifier}
        mismatched_identifiers = list(expected_identifiers.symmetric_difference(received_identifiers))
        if mismatched_identifiers:
            has_discrepancy = True

        for detail in details:
            if detail.stock_item.identifier in received_identifiers:
                detail.verification_status = "MATCHED"
                detail.stock_item.status = "AVAILABLE"  # now available at destination
            else:
                detail.verification_status = "DISCREPANCY"
            detail.save()
            detail.stock_item.save()

        # ---- Bulk items: credit destination Inventory with whatever actually arrived ----
        bulk_details = TransferBulkDetail.objects.filter(transfer=transfer)
        for bulk_detail in bulk_details:
            received_qty = received_bulk.get(bulk_detail.product_id, 0)
            bulk_detail.received_quantity = received_qty

            if received_qty != bulk_detail.shipped_quantity:
                has_discrepancy = True
                bulk_detail.verification_status = "DISCREPANCY"
                bulk_discrepancies.append({
                    "productId": bulk_detail.product_id,
                    "shipped": bulk_detail.shipped_quantity,
                    "received": received_qty,
                })
            else:
                bulk_detail.verification_status = "MATCHED"
            bulk_detail.save()

            if received_qty > 0:
                dest_inventory, _ = Inventory.objects.get_or_create(
                    shop=transfer.destination_shop, product_id=bulk_detail.product_id
                )
                dest_inventory.quantity += received_qty
                dest_inventory.save()

        transfer.status = "COMPLETED_WITH_DISCREPANCY" if has_discrepancy else "COMPLETED"
        transfer.save()

        return Response({
            "transferId": transfer.id,
            "status": transfer.status,
            "mismatchedIdentifiers": mismatched_identifiers,
            "bulkDiscrepancies": bulk_discrepancies,
        })


class TransferDetailView(APIView):
    """GET /transfers/{id} — STOCK_VIEW."""
    permission_classes = [HasPermission("STOCK_VIEW")]

    def get(self, request, transfer_id):
        transfer = get_object_or_404(Transfer, id=transfer_id)
        return Response(TransferSerializer(transfer).data)
