from rest_framework import serializers
from .models import Product


class ProductStaffSerializer(serializers.ModelSerializer):
    """Full detail — for staff roles. Includes buyingPrice (margin visibility)."""
    category = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "buying_price", "selling_price", "status", "category"]


class ProductCatalogueSerializer(serializers.ModelSerializer):
    """Customer-facing view — D-06 §9 catalogue privacy rule: no buyingPrice,
    no stock identifiers (IMEI/serial) ever exposed here."""
    category = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "selling_price", "status", "category"]


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["category", "name", "description", "buying_price", "selling_price"]

    def validate(self, attrs):
        if attrs["selling_price"] < attrs["buying_price"]:
            raise serializers.ValidationError("sellingPrice must be >= buyingPrice")
        return attrs
