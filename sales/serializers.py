from rest_framework import serializers
from .models import Sale, SaleDetail, Reservation, Favorite


class SaleItemSerializer(serializers.Serializer):
    productId = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)


class SaleCreateSerializer(serializers.Serializer):
    """POST /sales — BR-SALE-001/002 — D-12 §10."""
    shopId = serializers.IntegerField()
    userId = serializers.IntegerField()
    items = SaleItemSerializer(many=True)
    customerMTNNumber = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    deviceMTNNumber = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ["id", "shop", "user", "date", "total_amount", "customer_mtn_number", "device_mtn_number"]


class ReservationCreateSerializer(serializers.Serializer):
    productId = serializers.IntegerField()
    shopId = serializers.IntegerField()


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ["id", "user", "product", "shop", "status", "created_date"]


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "user", "product", "date_added"]
