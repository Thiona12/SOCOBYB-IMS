from rest_framework import serializers
from .models import StockRequest, Transfer, TransferDetail


class StockRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockRequest
        fields = ["id", "shop", "status", "date"]
        read_only_fields = ["id", "status", "date"]


class TransferCreateSerializer(serializers.Serializer):
    """POST /transfers — BR-TRF-001: created directly by management OR from an
    approved StockRequest (requestId optional/nullable)."""
    sourceShopId = serializers.IntegerField()
    destinationShopId = serializers.IntegerField()
    requestId = serializers.IntegerField(required=False, allow_null=True)
    stockItemIds = serializers.ListField(child=serializers.IntegerField())

    def validate(self, attrs):
        if attrs["sourceShopId"] == attrs["destinationShopId"]:
            raise serializers.ValidationError("sourceShopId and destinationShopId must differ")
        return attrs


class TransferVerifySerializer(serializers.Serializer):
    """POST /transfers/{id}/verify — BR-TRF-002: compare received identifiers
    against what was actually shipped; mismatch => COMPLETED_WITH_DISCREPANCY."""
    receivedIdentifiers = serializers.ListField(child=serializers.CharField())


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = ["id", "source_shop", "destination_shop", "request", "status", "date"]
