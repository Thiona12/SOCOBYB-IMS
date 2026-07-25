from decimal import Decimal
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from accounts.models import Shop, User
from accounts.permissions import HasPermission
from catalog.models import Product
from inventory.models import Inventory
from .models import Sale, SaleDetail, Reservation, Favorite
from .serializers import (
    SaleCreateSerializer, SaleSerializer, ReservationCreateSerializer,
    ReservationSerializer, FavoriteSerializer,
)


class SaleListCreateView(APIView):
    """POST/GET /sales — UC-08, BR-SALE-001/002 — D-12 §10.
    A successful sale reduces Inventory.quantity for bulk products (BR-SALE-001).
    Permission resolved per-method: STOCK_VIEW to create, REPORT_VIEW/VIEW_OWN_HISTORY to read."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission("STOCK_VIEW")()]
        return [IsAuthenticated()]

    @transaction.atomic
    def post(self, request):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        shop = get_object_or_404(Shop, id=data["shopId"])
        user = get_object_or_404(User, id=data["userId"])

        total = Decimal("0")
        details = []
        for item in data["items"]:
            product = get_object_or_404(Product, id=item["productId"])
            inventory = Inventory.objects.filter(shop=shop, product=product).first()
            if not inventory or inventory.quantity < item["quantity"]:
                return Response(
                    {"error": {"code": "STOCK_INSUFFICIENT", "message": f"Not enough stock for {product.name}"}},
                    status=409,
                )
            inventory.quantity -= item["quantity"]  # BR-SALE-001
            inventory.save()
            total += item["price"] * item["quantity"]
            details.append((product, item["quantity"], item["price"]))

        sale = Sale.objects.create(
            shop=shop, user=user, total_amount=total,
            customer_mtn_number=data.get("customerMTNNumber"),
            device_mtn_number=data.get("deviceMTNNumber"),
        )
        for product, qty, price in details:
            SaleDetail.objects.create(sale=sale, product=product, quantity=qty, price=price)

        # BR-SALE-002: if this sale fulfills a pending reservation for the same user+product, convert it.
        Reservation.objects.filter(
            user=user, product__in=[p for p, _, _ in details], status="PENDING"
        ).update(status="CONVERTED")

        return Response(SaleSerializer(sale).data, status=201)

    def get(self, request):
        user = request.user
        if user.has_perm_code("REPORT_VIEW"):
            sales = Sale.objects.all().order_by("-date")
        else:
            sales = Sale.objects.filter(user=user).order_by("-date")  # VIEW_OWN_HISTORY
        return Response({"data": SaleSerializer(sales, many=True).data})


class SaleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sale_id):
        sale = get_object_or_404(Sale, id=sale_id)
        if sale.user_id != request.user.id and not request.user.has_perm_code("REPORT_VIEW"):
            return Response({"error": {"code": "FORBIDDEN", "message": "Not your sale"}}, status=403)
        return Response(SaleSerializer(sale).data)


class ReservationCreateView(APIView):
    """POST /reservations — UC-09, BR-RES-001/003."""
    permission_classes = [HasPermission("RESERVATION_CREATE")]

    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        product = get_object_or_404(Product, id=data["productId"])
        shop = get_object_or_404(Shop, id=data["shopId"])
        # BR-RES-003: first-reserved-first-served is naturally enforced by created_date ordering
        # when the system later allocates available stock — no special write-time logic needed.
        reservation = Reservation.objects.create(user=request.user, product=product, shop=shop, status="PENDING")
        return Response(ReservationSerializer(reservation).data, status=201)


class MyReservationsView(APIView):
    permission_classes = [HasPermission("VIEW_OWN_HISTORY")]

    def get(self, request):
        reservations = Reservation.objects.filter(user=request.user).order_by("-created_date")
        return Response({"data": ReservationSerializer(reservations, many=True).data})


class ReservationCancelView(APIView):
    permission_classes = [HasPermission("RESERVATION_CREATE")]

    def patch(self, request, reservation_id):
        reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
        reservation.status = "CANCELLED"
        reservation.save()
        return Response(ReservationSerializer(reservation).data)


class FavoriteCreateView(APIView):
    permission_classes = [HasPermission("FAVORITE_CREATE")]

    def post(self, request):
        product = get_object_or_404(Product, id=request.data.get("productId"))
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
        return Response(FavoriteSerializer(favorite).data, status=201 if created else 200)


class MyFavoritesView(APIView):
    permission_classes = [HasPermission("VIEW_OWN_HISTORY")]

    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user)
        return Response({"data": FavoriteSerializer(favorites, many=True).data})


class FavoriteDeleteView(APIView):
    permission_classes = [HasPermission("FAVORITE_CREATE")]

    def delete(self, request, favorite_id):
        favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user)
        favorite.delete()
        return Response(status=204)
