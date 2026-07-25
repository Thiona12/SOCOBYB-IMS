from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from .models import Shop
from .shop_serializers import ShopSerializer
from .permissions import HasPermission


class ShopListCreateView(APIView):
    """GET/POST /api/v1/shops — UC-03 (D-04), D-12 §5."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission("USER_CREATE")()]
        return [IsAuthenticated()]

    def get(self, request):
        shops = Shop.objects.all()
        return Response({"data": ShopSerializer(shops, many=True).data})

    def post(self, request):
        serializer = ShopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = serializer.save()
        return Response(ShopSerializer(shop).data, status=201)


class ShopDetailView(APIView):
    """PATCH /api/v1/shops/{shopId} — BR-SHOP-001/002."""
    permission_classes = [HasPermission("USER_CREATE")]

    def patch(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        serializer = ShopSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
