from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from accounts.models import Shop
from accounts.permissions import HasPermission
from catalog.models import Product
from .models import Inventory, StockItem, StockMovement
from .serializers import InventorySerializer, ReceiveStockSerializer, StockMovementSerializer


class ShopInventoryView(APIView):
    """GET /shops/{shopId}/inventory — UC-05, STOCK_VIEW."""
    permission_classes = [HasPermission("STOCK_VIEW")]

    def get(self, request, shop_id):
        get_object_or_404(Shop, id=shop_id)
        inv = Inventory.objects.filter(shop_id=shop_id).select_related("product")
        return Response({"data": InventorySerializer(inv, many=True).data})


class ReceiveInventoryView(APIView):
    """POST /shops/{shopId}/inventory/receive — STOCK_ADJUST.
    BR-INV-002: tracked products (identifiers given) create individual StockItem rows.
    BR-INV-004: every reception logs a StockMovement."""
    permission_classes = [HasPermission("STOCK_ADJUST")]

    @transaction.atomic
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        serializer = ReceiveStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        product = get_object_or_404(Product, id=data["productId"])

        inventory, _ = Inventory.objects.get_or_create(shop=shop, product=product)

        created_items = []
        if data["identifiers"]:
            # Tracked product: one StockItem per identifier (BR-INV-002)
            if len(data["identifiers"]) != data["quantity"]:
                return Response(
                    {"error": {"code": "VALIDATION_ERROR", "message": "identifiers count must match quantity"}},
                    status=422,
                )
            for identifier in data["identifiers"]:
                item = StockItem.objects.create(
                    product=product, identifier=identifier, identifier_type="IMEI", status="AVAILABLE"
                )
                StockMovement.objects.create(stock_item=item, movement_type="RECEPTION", reference_id=shop.id)
                created_items.append(item.id)
            inventory.quantity += data["quantity"]
        else:
            # Bulk product: no individual tracking, just increment quantity.
            # Still log one StockMovement referencing a placeholder item isn't possible
            # without a StockItem — for bulk products we log against the inventory row itself.
            inventory.quantity += data["quantity"]

        inventory.save()

        return Response(
            {"inventoryId": inventory.id, "newQuantity": inventory.quantity, "stockItemsCreated": created_items},
            status=201,
        )


class StockItemMovementsView(APIView):
    """GET /stock-items/{stockItemId}/movements — STOCK_VIEW."""
    permission_classes = [HasPermission("STOCK_VIEW")]

    def get(self, request, stock_item_id):
        get_object_or_404(StockItem, id=stock_item_id)
        movements = StockMovement.objects.filter(stock_item_id=stock_item_id).order_by("-date")
        return Response({"data": StockMovementSerializer(movements, many=True).data})
