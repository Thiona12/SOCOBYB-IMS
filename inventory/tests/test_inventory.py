"""BR-INV-002 (tracked item identifiers) and BR-INV-004 (movement logging)."""
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.test_helpers import make_staff_user, make_shops
from catalog.models import Category, Product
from inventory.models import Inventory, StockItem, StockMovement


class InventoryReceptionTests(TestCase):
    def setUp(self):
        self.shop1, _ = make_shops()
        self.manager = make_staff_user("inv_manager", "SHOP_STOCK_MANAGER", shop=self.shop1)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(category=self.category, name="Phone V", buying_price=50000, selling_price=70000)
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)

    def test_receiving_tracked_product_creates_stock_items(self):
        resp = self.client.post(f"/api/v1/shops/{self.shop1.id}/inventory/receive", {
            "productId": self.product.id, "quantity": 2, "identifiers": ["IMEI-X1", "IMEI-X2"],
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(StockItem.objects.filter(product=self.product).count(), 2)
        self.assertEqual(StockMovement.objects.filter(movement_type="RECEPTION").count(), 2)

    def test_receiving_bulk_product_increments_quantity_only(self):
        resp = self.client.post(f"/api/v1/shops/{self.shop1.id}/inventory/receive", {
            "productId": self.product.id, "quantity": 15,
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(StockItem.objects.filter(product=self.product).count(), 0)
        inv = Inventory.objects.get(shop=self.shop1, product=self.product)
        self.assertEqual(inv.quantity, 15)

    def test_mismatched_identifier_count_rejected(self):
        resp = self.client.post(f"/api/v1/shops/{self.shop1.id}/inventory/receive", {
            "productId": self.product.id, "quantity": 3, "identifiers": ["IMEI-Y1", "IMEI-Y2"],
        }, format="json")
        self.assertEqual(resp.status_code, 422)

    def test_unauthorized_role_cannot_receive_stock(self):
        from accounts.test_helpers import make_customer
        customer = make_customer("inv_customer_test")
        self.client.force_authenticate(user=customer)
        resp = self.client.post(f"/api/v1/shops/{self.shop1.id}/inventory/receive", {
            "productId": self.product.id, "quantity": 5,
        }, format="json")
        self.assertEqual(resp.status_code, 403)
