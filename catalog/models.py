from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_CHOICES = [("ACTIVE", "Active"), ("DISCONTINUED", "Discontinued")]

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    buying_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="ACTIVE")

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name
