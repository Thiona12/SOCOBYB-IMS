from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .serializers import RegisterSerializer, LoginSerializer


class RegisterView(APIView):
    """POST /api/v1/auth/register — public (D-12 §3)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"userId": user.id, "userNumber": user.user_number, "role": "CUSTOMER"},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/v1/auth/login — public (D-12 §3)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response(serializer.to_token_response(user), status=status.HTTP_200_OK)


class MeView(APIView):
    """GET /api/v1/users/me."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "userId": user.id,
            "userNumber": user.user_number,
            "name": user.name,
            "phone": user.phone,
            "roles": list(user.roles.values_list("name", flat=True)),
        })
