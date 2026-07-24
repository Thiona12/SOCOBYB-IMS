from django.db import models
from accounts.models import Shop
from inventory.models import StockItem


class StockRequest(models.Model):
    STATUS_CHOICES = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="stock_requests")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_requests"


class Transfer(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"), ("IN_TRANSIT", "In transit"),
        ("COMPLETED", "Completed"), ("COMPLETED_WITH_DISCREPANCY", "Completed with discrepancy"),
    ]

    source_shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="transfers_out")
    destination_shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="transfers_in")
    request = models.ForeignKey(StockRequest, on_delete=models.SET_NULL, null=True, blank=True,
                                 help_text="NULL when created directly by management (BR-TRF-001)")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transfers"


class TransferDetail(models.Model):
    VERIFICATION_CHOICES = [("PENDING", "Pending"), ("MATCHED", "Matched"), ("DISCREPANCY", "Discrepancy")]

    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name="details")
    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE)
    verification_status = models.CharField(max_length=12, choices=VERIFICATION_CHOICES, default="PENDING")

    class Meta:
        db_table = "transfer_details"
