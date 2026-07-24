from django.contrib import admin
from .models import StockRequest, Transfer, TransferDetail

admin.site.register(StockRequest)
admin.site.register(Transfer)
admin.site.register(TransferDetail)
