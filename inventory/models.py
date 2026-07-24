from django.db import models
from accounts.models import Shop
from catalog.models import Product


class StockItem(models.Model):
    IDENTIFIER_TYPES = [("IMEI", "IMEI"), ("SERIAL", "Serial"), ("NONE", "None")]
    STATUS_CHOICES = [
        ("AVAILABLE", "Available"), ("RESERVED", "Reserved"), ("ASSIGNED", "Assigned"),
        ("SOLD", "Sold"), ("DAMAGED", "Damaged"), ("LOST", "Lost"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_items")
    identifier = models.CharField(max_length=50, unique=True, null=True, blank=True)
    identifier_type = models.CharField(max_length=10, choices=IDENTIFIER_TYPES, default="NONE")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="AVAILABLE")

    class Meta:
        db_table = "stock_items"


class Inventory(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="inventories")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventories")
    quantity = models.PositiveIntegerField(default=0)
    minimum_level = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "inventories"
        unique_together = ("shop", "product")


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ("RECEPTION", "Reception"), ("SALE", "Sale"), ("TRANSFER", "Transfer"),
        ("ASSIGNMENT", "Assignment"), ("ADJUSTMENT", "Adjustment"),
    ]

    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=12, choices=MOVEMENT_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    reference_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "stock_movements"
