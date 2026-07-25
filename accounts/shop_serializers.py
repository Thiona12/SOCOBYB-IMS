from rest_framework import serializers
from .models import Shop


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name", "location", "status", "created_date"]
        read_only_fields = ["id", "created_date"]
