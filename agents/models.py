from django.db import models
from inventory.models import StockItem


class Agent(models.Model):
    STATUS_CHOICES = [("APPROVED", "Approved"), ("PENDING", "Pending"), ("SUSPENDED", "Suspended")]

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "agents"


class Assignment(models.Model):
    STATUS_CHOICES = [("ACTIVE", "Active"), ("CLOSED", "Closed")]

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="assignments")
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")

    class Meta:
        db_table = "assignments"


class AssignmentDetail(models.Model):
    PAYMENT_STATUS = [("UNPAID", "Unpaid"), ("PAID", "Paid")]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="details")
    stock_item = models.OneToOneField(StockItem, on_delete=models.CASCADE)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="UNPAID")

    class Meta:
        db_table = "assignment_details"
