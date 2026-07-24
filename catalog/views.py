from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from accounts.permissions import HasPermission
from .models import Product
from .serializers import ProductStaffSerializer, ProductCatalogueSerializer, ProductCreateSerializer


class ProductListCreateView(APIView):
    """GET/POST /api/v1/products — UC-04 (D-04), D-12 §6."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_customer_only = (
            request.user.roles.count() == 1 and
            request.user.roles.filter(name="CUSTOMER").exists()
        )
        products = Product.objects.filter(status="ACTIVE").select_related("category")
        serializer_cls = ProductCatalogueSerializer if is_customer_only else ProductStaffSerializer
        return Response({"data": serializer_cls(products, many=True).data})

    def post(self, request):
        self.check_permissions(request)
        if not request.user.has_perm_code("PRODUCT_CREATE"):
            return Response({"error": {"code": "FORBIDDEN", "message": "Missing permission: PRODUCT_CREATE"}}, status=403)
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response({"productId": product.id}, status=status.HTTP_201_CREATED)
