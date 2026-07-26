"""Shared test fixtures — seeds the minimal roles/permissions/shops needed
by tests across apps, mirroring the seed data in socobyb_schema.sql."""
from accounts.models import Role, Permission, RolePermission, User, UserRole, Shop

ALL_PERMISSIONS = [
    "USER_CREATE", "PRODUCT_CREATE", "STOCK_VIEW", "STOCK_ADJUST",
    "TRANSFER_CREATE", "TRANSFER_APPROVE", "AGENT_APPROVE", "REPORT_VIEW",
    "RESERVATION_CREATE", "FAVORITE_CREATE", "VIEW_OWN_HISTORY",
]

ROLE_PERMISSIONS = {
    "GENERAL_ADMINISTRATOR": ["USER_CREATE", "PRODUCT_CREATE", "REPORT_VIEW"],
    "GENERAL_STOCK_MANAGER": ["STOCK_VIEW", "TRANSFER_APPROVE", "AGENT_APPROVE", "REPORT_VIEW"],
    "SHOP_ADMINISTRATOR": ["USER_CREATE"],
    "SHOP_STOCK_MANAGER": ["STOCK_VIEW", "STOCK_ADJUST", "TRANSFER_CREATE", "PRODUCT_CREATE"],
    "CUSTOMER": ["RESERVATION_CREATE", "FAVORITE_CREATE", "VIEW_OWN_HISTORY"],
}


def seed_roles_and_permissions():
    for code in ALL_PERMISSIONS:
        Permission.objects.get_or_create(code=code)
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role, _ = Role.objects.get_or_create(name=role_name)
        for code in perm_codes:
            RolePermission.objects.get_or_create(role=role, permission=Permission.objects.get(code=code))


def make_staff_user(username, role_name, shop=None, password="testpass123"):
    seed_roles_and_permissions()
    user = User.objects.create_user(
        username=username, name=f"{username} name", phone="677000000",
        password=password, user_number=f"STAFF-{username}", shop=shop,
    )
    role = Role.objects.get(name=role_name)
    UserRole.objects.get_or_create(user=user, role=role)
    return user


def make_customer(username, password="testpass123"):
    seed_roles_and_permissions()
    user = User.objects.create_user(
        username=username, name=f"{username} name", phone="677111111",
        password=password, user_number=f"CUST-{username}",
    )
    role, _ = Role.objects.get_or_create(name="CUSTOMER")
    UserRole.objects.get_or_create(user=user, role=role)
    return user


def make_shops():
    s1 = Shop.objects.create(name="Boutique A", location="Garoua A")
    s2 = Shop.objects.create(name="Boutique B", location="Garoua B")
    return s1, s2
