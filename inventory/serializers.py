from rest_framework import serializers
from .models import Inventory, StockItem, StockMovement


class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Inventory
        fields = ["id", "shop", "product", "product_name", "quantity", "minimum_level"]


class ReceiveStockSerializer(serializers.Serializer):
    """POST /shops/{shopId}/inventory/receive — D-12 §7.
    Creates StockItem rows (tracked products) or increments Inventory.quantity
    (bulk products), and always logs a StockMovement (BR-INV-004)."""
    productId = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    identifiers = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ["id", "stock_item", "movement_type", "date", "reference_id"]
