"""BR-TRF-001 (creation/reservation) and BR-TRF-002 (IMEI + bulk discrepancy detection)."""
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.test_helpers import make_staff_user, make_shops
from catalog.models import Category, Product
from inventory.models import Inventory, StockItem
from stockops.models import Transfer


class TransferTrackedItemsTests(TestCase):
    def setUp(self):
        self.shop1, self.shop2 = make_shops()
        self.manager = make_staff_user("manager1", "SHOP_STOCK_MANAGER", shop=self.shop1)
        self.gsm = make_staff_user("gsm1", "GENERAL_STOCK_MANAGER")
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(category=self.category, name="Phone X", buying_price=50000, selling_price=70000)
        self.item1 = StockItem.objects.create(product=self.product, identifier="IMEI-1", identifier_type="IMEI", status="AVAILABLE")
        self.item2 = StockItem.objects.create(product=self.product, identifier="IMEI-2", identifier_type="IMEI", status="AVAILABLE")
        self.client = APIClient()

    def test_create_transfer_reserves_stock_items(self):
        self.client.force_authenticate(user=self.manager)
        resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "stockItemIds": [self.item1.id, self.item2.id],
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.status, "RESERVED")

    def test_verify_matching_identifiers_completes_cleanly(self):
        self.client.force_authenticate(user=self.manager)
        transfer_resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "stockItemIds": [self.item1.id, self.item2.id],
        }, format="json")
        transfer_id = transfer_resp.data["id"]

        self.client.force_authenticate(user=self.gsm)
        verify_resp = self.client.post(f"/api/v1/transfers/{transfer_id}/verify", {
            "receivedIdentifiers": ["IMEI-1", "IMEI-2"],
        }, format="json")
        self.assertEqual(verify_resp.data["status"], "COMPLETED")
        self.assertEqual(verify_resp.data["mismatchedIdentifiers"], [])

    def test_verify_with_wrong_identifier_flags_discrepancy(self):
        """The exact scenario I tested manually earlier: IMEI-2 swapped for a wrong one."""
        self.client.force_authenticate(user=self.manager)
        transfer_resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "stockItemIds": [self.item1.id, self.item2.id],
        }, format="json")
        transfer_id = transfer_resp.data["id"]

        self.client.force_authenticate(user=self.gsm)
        verify_resp = self.client.post(f"/api/v1/transfers/{transfer_id}/verify", {
            "receivedIdentifiers": ["IMEI-1", "IMEI-WRONG"],
        }, format="json")
        self.assertEqual(verify_resp.data["status"], "COMPLETED_WITH_DISCREPANCY")
        self.assertIn("IMEI-2", verify_resp.data["mismatchedIdentifiers"])
        self.assertIn("IMEI-WRONG", verify_resp.data["mismatchedIdentifiers"])

    def test_cannot_transfer_unavailable_stock_item(self):
        self.item1.status = "SOLD"
        self.item1.save()
        self.client.force_authenticate(user=self.manager)
        resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "stockItemIds": [self.item1.id],
        }, format="json")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["error"]["code"], "STOCK_INSUFFICIENT")


class TransferBulkItemsTests(TestCase):
    """The bulk-transfer fix — verifies Inventory.quantity actually moves."""

    def setUp(self):
        self.shop1, self.shop2 = make_shops()
        self.manager = make_staff_user("manager2", "SHOP_STOCK_MANAGER", shop=self.shop1)
        self.gsm = make_staff_user("gsm2", "GENERAL_STOCK_MANAGER")
        self.category = Category.objects.create(name="Accessories")
        self.product = Product.objects.create(category=self.category, name="Charger", buying_price=1500, selling_price=2500)
        Inventory.objects.create(shop=self.shop1, product=self.product, quantity=20)
        self.client = APIClient()

    def test_create_bulk_transfer_reserves_source_quantity(self):
        self.client.force_authenticate(user=self.manager)
        resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "bulkItems": [{"productId": self.product.id, "quantity": 8}],
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        source_inv = Inventory.objects.get(shop=self.shop1, product=self.product)
        self.assertEqual(source_inv.quantity, 12)  # 20 - 8

    def test_verify_matching_bulk_quantity_credits_destination(self):
        self.client.force_authenticate(user=self.manager)
        transfer_resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "bulkItems": [{"productId": self.product.id, "quantity": 8}],
        }, format="json")
        transfer_id = transfer_resp.data["id"]

        self.client.force_authenticate(user=self.gsm)
        verify_resp = self.client.post(f"/api/v1/transfers/{transfer_id}/verify", {
            "receivedBulkItems": [{"productId": self.product.id, "quantity": 8}],
        }, format="json")
        self.assertEqual(verify_resp.data["status"], "COMPLETED")
        dest_inv = Inventory.objects.get(shop=self.shop2, product=self.product)
        self.assertEqual(dest_inv.quantity, 8)

    def test_short_delivery_flags_discrepancy(self):
        """The exact scenario I tested manually: 5 shipped, 3 received."""
        self.client.force_authenticate(user=self.manager)
        transfer_resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "bulkItems": [{"productId": self.product.id, "quantity": 5}],
        }, format="json")
        transfer_id = transfer_resp.data["id"]

        self.client.force_authenticate(user=self.gsm)
        verify_resp = self.client.post(f"/api/v1/transfers/{transfer_id}/verify", {
            "receivedBulkItems": [{"productId": self.product.id, "quantity": 3}],
        }, format="json")
        self.assertEqual(verify_resp.data["status"], "COMPLETED_WITH_DISCREPANCY")
        self.assertEqual(verify_resp.data["bulkDiscrepancies"][0]["shipped"], 5)
        self.assertEqual(verify_resp.data["bulkDiscrepancies"][0]["received"], 3)
        # Destination still gets credited with what actually arrived (3), not 0 or 5.
        dest_inv = Inventory.objects.get(shop=self.shop2, product=self.product)
        self.assertEqual(dest_inv.quantity, 3)

    def test_insufficient_source_stock_rejected(self):
        self.client.force_authenticate(user=self.manager)
        resp = self.client.post("/api/v1/transfers", {
            "sourceShopId": self.shop1.id, "destinationShopId": self.shop2.id,
            "bulkItems": [{"productId": self.product.id, "quantity": 999}],
        }, format="json")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["error"]["code"], "STOCK_INSUFFICIENT")
