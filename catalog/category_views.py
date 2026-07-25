from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Category
from .category_serializers import CategorySerializer
from accounts.permissions import HasPermission


class CategoryListCreateView(APIView):
    """GET/POST /api/v1/categories — UC-04, D-12 §6."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission("PRODUCT_CREATE")()]
        return [IsAuthenticated()]

    def get(self, request):
        categories = Category.objects.all()
        return Response({"data": CategorySerializer(categories, many=True).data})

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(CategorySerializer(category).data, status=201)
