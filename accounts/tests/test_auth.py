"""D-08 hybrid permission model + auth flow (D-12 §3)."""
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User, Role, Permission, RolePermission, UserRole, UserPermission
from accounts.test_helpers import make_staff_user, make_customer, seed_roles_and_permissions


class RegisterLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_customer_role(self):
        resp = self.client.post("/api/v1/auth/register", {
            "name": "Aissatou B.", "phone": "677123456", "username": "aissatou", "password": "testpass123",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["role"], "CUSTOMER")
        user = User.objects.get(username="aissatou")
        self.assertTrue(user.roles.filter(name="CUSTOMER").exists())

    def test_register_rejects_duplicate_username(self):
        make_customer("dupuser")
        resp = self.client.post("/api/v1/auth/register", {
            "name": "X", "phone": "677000000", "username": "dupuser", "password": "testpass123",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_login_success_returns_token(self):
        make_customer("client1")
        resp = self.client.post("/api/v1/auth/login", {"username": "client1", "password": "testpass123"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.data)

    def test_login_wrong_password_rejected(self):
        make_customer("client2")
        resp = self.client.post("/api/v1/auth/login", {"username": "client2", "password": "wrongpass"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_inactive_account_rejected(self):
        user = make_customer("inactive1")
        user.status = "INACTIVE"
        user.save()
        resp = self.client.post("/api/v1/auth/login", {"username": "inactive1", "password": "testpass123"}, format="json")
        self.assertEqual(resp.status_code, 400)


class HybridPermissionModelTests(TestCase):
    """D-08 §3: a permission can come from a Role OR be granted directly to the User."""

    def setUp(self):
        seed_roles_and_permissions()

    def test_permission_via_role(self):
        user = make_staff_user("gsm_via_role", "GENERAL_STOCK_MANAGER")
        self.assertTrue(user.has_perm_code("TRANSFER_APPROVE"))

    def test_permission_not_granted_is_denied(self):
        user = make_staff_user("customer_role_only", "CUSTOMER")
        self.assertFalse(user.has_perm_code("AGENT_APPROVE"))

    def test_direct_user_permission_without_role(self):
        """A user with NO role granting AGENT_APPROVE should still pass if it's
        granted directly — this is the exact bug I found and fixed earlier
        (related_name was pointing the wrong direction)."""
        user = make_staff_user("temp_grant", "SHOP_STOCK_MANAGER")
        self.assertFalse(user.has_perm_code("AGENT_APPROVE"))  # not via role
        UserPermission.objects.create(user=user, permission=Permission.objects.get(code="AGENT_APPROVE"))
        self.assertTrue(user.has_perm_code("AGENT_APPROVE"))  # now via direct grant


class ProductCataloguePrivacyTests(TestCase):
    """D-06 §9: Customer role must never see buying_price."""

    def setUp(self):
        from catalog.models import Category, Product
        seed_roles_and_permissions()
        self.client = APIClient()
        self.category = Category.objects.create(name="Telephones")
        self.product = Product.objects.create(category=self.category, name="Test Phone", buying_price=85000, selling_price=110000)

    def test_customer_does_not_see_buying_price(self):
        customer = make_customer("privacytest")
        self.client.force_authenticate(user=customer)
        resp = self.client.get("/api/v1/products")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("buying_price", resp.data["data"][0])

    def test_staff_sees_buying_price(self):
        staff = make_staff_user("staffprivacy", "SHOP_STOCK_MANAGER")
        self.client.force_authenticate(user=staff)
        resp = self.client.get("/api/v1/products")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("buying_price", resp.data["data"][0])

    def test_selling_price_must_not_be_below_buying_price(self):
        staff = make_staff_user("pricevalidation", "SHOP_STOCK_MANAGER")
        self.client.force_authenticate(user=staff)
        resp = self.client.post("/api/v1/products", {
            "category": self.category.id, "name": "Bad Product", "buying_price": 10000, "selling_price": 5000,
        }, format="json")
        self.assertEqual(resp.status_code, 400)
