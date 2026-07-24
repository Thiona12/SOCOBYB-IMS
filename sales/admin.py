from django.contrib import admin
from .models import Favorite, Reservation, Sale, SaleDetail

admin.site.register(Favorite)
admin.site.register(Reservation)
admin.site.register(Sale)
admin.site.register(SaleDetail)
