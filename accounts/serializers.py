from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Role, UserRole
import time


class RegisterSerializer(serializers.Serializer):
    """UC-13 — Customer self-registration (D-04)."""
    name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    username = serializers.CharField(max_length=50, min_length=3)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already in use")
        return value

    def create(self, validated_data):
        user_number = f"CUST-{str(int(time.time()))[-6:]}"
        user = User.objects.create_user(
            username=validated_data["username"],
            name=validated_data["name"],
            phone=validated_data["phone"],
            password=validated_data["password"],
            user_number=user_number,
        )
        customer_role, _ = Role.objects.get_or_create(name="CUSTOMER")
        UserRole.objects.create(user=user, role=customer_role)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            user = User.objects.get(username=attrs["username"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid username or password")

        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid username or password")
        if user.status != "ACTIVE":
            raise serializers.ValidationError("Account is inactive")

        attrs["user"] = user
        return attrs

    def to_token_response(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "token": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "userId": user.id,
                "name": user.name,
                "roles": list(user.roles.values_list("name", flat=True)),
            },
        }
