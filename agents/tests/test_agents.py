"""BR-AGT-002/003 (credit limit) and BR-AGT-004 (payment status transition)."""
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.test_helpers import make_staff_user
from agents.models import Agent, AssignmentDetail
from catalog.models import Category, Product
from inventory.models import StockItem


class AgentCreditLimitTests(TestCase):
    def setUp(self):
        self.gsm = make_staff_user("gsm_agent_test", "GENERAL_STOCK_MANAGER")
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(category=self.category, name="Phone Y", buying_price=50000, selling_price=70000)
        self.client = APIClient()
        self.client.force_authenticate(user=self.gsm)

    def test_assignment_within_credit_limit_succeeds(self):
        agent = Agent.objects.create(name="Agent A", phone="677000000", credit_limit=2, status="APPROVED")
        item1 = StockItem.objects.create(product=self.product, identifier="IMEI-A1", status="AVAILABLE")
        item2 = StockItem.objects.create(product=self.product, identifier="IMEI-A2", status="AVAILABLE")

        resp = self.client.post(f"/api/v1/agents/{agent.id}/assignments", {
            "stockItemIds": [item1.id, item2.id],
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        item1.refresh_from_db()
        self.assertEqual(item1.status, "ASSIGNED")

    def test_assignment_exceeding_credit_limit_rejected(self):
        """The exact scenario tested manually: limit=1, requesting 2."""
        agent = Agent.objects.create(name="Agent B", phone="677000001", credit_limit=1, status="APPROVED")
        item1 = StockItem.objects.create(product=self.product, identifier="IMEI-B1", status="AVAILABLE")
        item2 = StockItem.objects.create(product=self.product, identifier="IMEI-B2", status="AVAILABLE")

        resp = self.client.post(f"/api/v1/agents/{agent.id}/assignments", {
            "stockItemIds": [item1.id, item2.id],
        }, format="json")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["error"]["code"], "CREDIT_LIMIT_EXCEEDED")
        item1.refresh_from_db()
        self.assertEqual(item1.status, "AVAILABLE")  # nothing was assigned

    def test_existing_outstanding_counts_toward_limit(self):
        """Credit limit check considers ALREADY-outstanding unpaid devices, not just the new request."""
        agent = Agent.objects.create(name="Agent C", phone="677000002", credit_limit=2, status="APPROVED")
        item1 = StockItem.objects.create(product=self.product, identifier="IMEI-C1", status="AVAILABLE")
        self.client.post(f"/api/v1/agents/{agent.id}/assignments", {"stockItemIds": [item1.id]}, format="json")

        item2 = StockItem.objects.create(product=self.product, identifier="IMEI-C2", status="AVAILABLE")
        item3 = StockItem.objects.create(product=self.product, identifier="IMEI-C3", status="AVAILABLE")
        resp = self.client.post(f"/api/v1/agents/{agent.id}/assignments", {
            "stockItemIds": [item2.id, item3.id],
        }, format="json")
        # 1 outstanding + 2 new = 3 > limit of 2
        self.assertEqual(resp.status_code, 409)

    def test_payment_marks_stock_item_sold(self):
        agent = Agent.objects.create(name="Agent D", phone="677000003", credit_limit=5, status="APPROVED")
        item = StockItem.objects.create(product=self.product, identifier="IMEI-D1", status="AVAILABLE")
        self.client.post(f"/api/v1/agents/{agent.id}/assignments", {"stockItemIds": [item.id]}, format="json")
        detail = AssignmentDetail.objects.get(stock_item=item)

        resp = self.client.patch(f"/api/v1/assignment-details/{detail.id}/pay")
        self.assertEqual(resp.status_code, 200)
        detail.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(detail.payment_status, "PAID")
        self.assertEqual(item.status, "SOLD")


class AgentPermissionTests(TestCase):
    def test_customer_cannot_manage_agents(self):
        from accounts.test_helpers import make_customer
        customer = make_customer("agent_perm_test")
        client = APIClient()
        client.force_authenticate(user=customer)
        resp = client.get("/api/v1/agents")
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_request_rejected(self):
        client = APIClient()
        resp = client.get("/api/v1/agents")
        self.assertEqual(resp.status_code, 401)
