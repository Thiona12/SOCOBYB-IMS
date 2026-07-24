"""
accounts/models.py — implements D-07 §1 and D-08's hybrid permission model:
a User is authorized via Role -> RolePermission -> Permission, OR via a
direct UserPermission grant. Customer is just another Role (D-06 §6 decision).
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Shop(models.Model):
    STATUS_CHOICES = [("ACTIVE", "Active"), ("INACTIVE", "Inactive")]

    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shops"

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.name


class Permission(models.Model):
    code = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        db_table = "role_permissions"
        unique_together = ("role", "permission")


class UserManager(BaseUserManager):
    def create_user(self, username, name, phone, password=None, **extra):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username, name=name, phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, name, phone, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(username, name, phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Represents BOTH staff and customers, distinguished by Role — the confirmed
    D-06/D-07 decision to unify Customer into User rather than a separate entity."""

    STATUS_CHOICES = [("ACTIVE", "Active"), ("INACTIVE", "Inactive")]

    user_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    username = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    created_date = models.DateTimeField(auto_now_add=True)
    shop = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="staff", help_text="NULL for customers")

    roles = models.ManyToManyField(Role, through="UserRole", related_name="users")
    direct_permissions = models.ManyToManyField(Permission, through="UserPermission", related_name="direct_users")

    is_staff = models.BooleanField(default=False)  # Django admin access, not business "staff"

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name", "phone"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name} ({self.username})"

    def resolved_permissions(self):
        """Union of role_permissions and direct user_permissions — D-08 §3 hybrid model."""
        via_roles = Permission.objects.filter(role_permissions__role__users=self)
        via_direct = self.direct_permissions.all()
        return (via_roles | via_direct).distinct().values_list("code", flat=True)

    def has_perm_code(self, code):
        return code in self.resolved_permissions()


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        db_table = "user_roles"
        unique_together = ("user", "role")


class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = "user_permissions"
        unique_together = ("user", "permission")
