"""BR-SALE-001 (inventory reduction) and BR-SALE-002 (reservation conversion)."""
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.test_helpers import make_staff_user, make_customer, make_shops
from catalog.models import Category, Product
from inventory.models import Inventory
from sales.models import Reservation, Sale


class SaleReducesInventoryTests(TestCase):
    def setUp(self):
        self.shop1, _ = make_shops()
        self.manager = make_staff_user("sale_manager", "SHOP_STOCK_MANAGER", shop=self.shop1)
        self.customer = make_customer("sale_customer")
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(category=self.category, name="Phone Z", buying_price=50000, selling_price=70000)
        Inventory.objects.create(shop=self.shop1, product=self.product, quantity=10)
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)

    def test_sale_reduces_inventory_by_quantity_sold(self):
        """The exact scenario tested manually: 7 in stock, sell 3, expect 4 left."""
        resp = self.client.post("/api/v1/sales", {
            "shopId": self.shop1.id, "userId": self.customer.id,
            "items": [{"productId": self.product.id, "quantity": 3, "price": 70000}],
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        inv = Inventory.objects.get(shop=self.shop1, product=self.product)
        self.assertEqual(inv.quantity, 7)  # 10 - 3

    def test_sale_with_insufficient_stock_rejected(self):
        resp = self.client.post("/api/v1/sales", {
            "shopId": self.shop1.id, "userId": self.customer.id,
            "items": [{"productId": self.product.id, "quantity": 999, "price": 70000}],
        }, format="json")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["error"]["code"], "STOCK_INSUFFICIENT")
        inv = Inventory.objects.get(shop=self.shop1, product=self.product)
        self.assertEqual(inv.quantity, 10)  # unchanged

    def test_sale_records_mtn_fields(self):
        """The restored design decision: MTN numbers belong on Sale, not StockItem."""
        resp = self.client.post("/api/v1/sales", {
            "shopId": self.shop1.id, "userId": self.customer.id,
            "items": [{"productId": self.product.id, "quantity": 1, "price": 70000}],
            "customerMTNNumber": "677123456", "deviceMTNNumber": "677998877",
        }, format="json")
        sale = Sale.objects.get(id=resp.data["id"])
        self.assertEqual(sale.customer_mtn_number, "677123456")
        self.assertEqual(sale.device_mtn_number, "677998877")

    def test_sale_converts_matching_pending_reservation(self):
        """BR-SALE-002."""
        Reservation.objects.create(user=self.customer, product=self.product, shop=self.shop1, status="PENDING")
        self.client.post("/api/v1/sales", {
            "shopId": self.shop1.id, "userId": self.customer.id,
            "items": [{"productId": self.product.id, "quantity": 1, "price": 70000}],
        }, format="json")
        reservation = Reservation.objects.get(user=self.customer, product=self.product)
        self.assertEqual(reservation.status, "CONVERTED")


class ReservationTests(TestCase):
    def setUp(self):
        self.shop1, _ = make_shops()
        self.customer = make_customer("res_customer")
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(category=self.category, name="Phone W", buying_price=50000, selling_price=70000)
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def test_customer_can_reserve_product(self):
        resp = self.client.post("/api/v1/reservations", {
            "productId": self.product.id, "shopId": self.shop1.id,
        }, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_customer_can_cancel_own_reservation(self):
        create_resp = self.client.post("/api/v1/reservations", {
            "productId": self.product.id, "shopId": self.shop1.id,
        }, format="json")
        reservation_id = create_resp.data["id"]
        cancel_resp = self.client.patch(f"/api/v1/reservations/{reservation_id}/cancel")
        self.assertEqual(cancel_resp.status_code, 200)
        self.assertEqual(cancel_resp.data["status"], "CANCELLED")
