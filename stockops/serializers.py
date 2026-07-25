from rest_framework import serializers
from .models import StockRequest, Transfer, TransferDetail


class StockRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockRequest
        fields = ["id", "shop", "status", "date"]
        read_only_fields = ["id", "status", "date"]


class TransferBulkItemSerializer(serializers.Serializer):
    productId = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class TransferCreateSerializer(serializers.Serializer):
    """POST /transfers — BR-TRF-001: created directly by management OR from an
    approved StockRequest (requestId optional/nullable). Supports tracked items
    (stockItemIds — IMEI/serial) and bulk items (bulkItems — quantity-only products)
    in the same transfer."""
    sourceShopId = serializers.IntegerField()
    destinationShopId = serializers.IntegerField()
    requestId = serializers.IntegerField(required=False, allow_null=True)
    stockItemIds = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    bulkItems = TransferBulkItemSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        if attrs["sourceShopId"] == attrs["destinationShopId"]:
            raise serializers.ValidationError("sourceShopId and destinationShopId must differ")
        if not attrs.get("stockItemIds") and not attrs.get("bulkItems"):
            raise serializers.ValidationError("Provide at least one of stockItemIds or bulkItems")
        return attrs


class TransferVerifySerializer(serializers.Serializer):
    """POST /transfers/{id}/verify — BR-TRF-002: compare received identifiers/quantities
    against what was actually shipped; mismatch => COMPLETED_WITH_DISCREPANCY."""
    receivedIdentifiers = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    receivedBulkItems = TransferBulkItemSerializer(many=True, required=False, default=list)


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = ["id", "source_shop", "destination_shop", "request", "status", "date"]
