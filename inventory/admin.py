from django.contrib import admin
from .models import StockItem, Inventory, StockMovement

admin.site.register(StockItem)
admin.site.register(Inventory)
admin.site.register(StockMovement)
