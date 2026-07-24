from django.db import models
from django.conf import settings
from accounts.models import Shop
from catalog.models import Product


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date_added = models.DateField(auto_now_add=True)

    class Meta:
        db_table = "favorites"
        unique_together = ("user", "product")


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"), ("CONVERTED", "Converted"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reservations"


class Sale(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="sales")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    customer_mtn_number = models.CharField(max_length=20, null=True, blank=True)
    device_mtn_number = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "sales"


class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="details")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "sale_details"
