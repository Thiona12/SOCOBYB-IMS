"""Session-based frontend tests — verifies the web UI wiring, not just the API."""
from django.test import TestCase
from accounts.test_helpers import make_staff_user, make_customer, make_shops
from catalog.models import Category, Product
from inventory.models import Inventory


class WebRegistrationLoginTests(TestCase):
    def test_register_logs_in_and_redirects_to_dashboard(self):
        resp = self.client.post("/register/", {
            "name": "Web Client", "phone": "677222222", "username": "webclient", "password": "webpass123",
        })
        self.assertEqual(resp.status_code, 302)
        # Customer should land on the catalogue, not the staff dashboard.
        resp2 = self.client.get("/", follow=True)
        self.assertRedirects(resp2, "/catalogue/")

    def test_staff_login_reaches_dashboard(self):
        make_staff_user("web_manager", "SHOP_STOCK_MANAGER")
        self.client.login(username="web_manager", password="testpass123")
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tableau de bord")

    def test_anonymous_user_redirected_to_login(self):
        resp = self.client.get("/inventory/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)


class WebCatalogueTests(TestCase):
    def setUp(self):
        self.shop, _ = make_shops()
        self.customer = make_customer("web_catalogue_customer")
        category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(category=category, name="Web Phone", buying_price=50000, selling_price=70000)
        self.client.login(username="web_catalogue_customer", password="testpass123")

    def test_catalogue_shows_product_and_hides_buying_price(self):
        resp = self.client.get("/catalogue/")
        self.assertContains(resp, "Web Phone")
        self.assertNotContains(resp, "50000")  # buying price never rendered

    def test_reserve_product_creates_reservation(self):
        from sales.models import Reservation
        self.client.post(f"/catalogue/{self.product.id}/reserve/", {"shop_id": self.shop.id})
        self.assertTrue(Reservation.objects.filter(user=self.customer, product=self.product).exists())

    def test_toggle_favorite_adds_and_removes(self):
        from sales.models import Favorite
        self.client.post(f"/catalogue/{self.product.id}/favorite/")
        self.assertTrue(Favorite.objects.filter(user=self.customer, product=self.product).exists())
        self.client.post(f"/catalogue/{self.product.id}/favorite/")
        self.assertFalse(Favorite.objects.filter(user=self.customer, product=self.product).exists())


class WebTransferFlowTests(TestCase):
    def setUp(self):
        self.shop1, self.shop2 = make_shops()
        make_staff_user("web_transfer_manager", "SHOP_STOCK_MANAGER", shop=self.shop1)
        make_staff_user("web_transfer_approver", "GENERAL_STOCK_MANAGER")
        category = Category.objects.create(name="Accessories")
        self.product = Product.objects.create(category=category, name="Cable", buying_price=1000, selling_price=2000)
        Inventory.objects.create(shop=self.shop1, product=self.product, quantity=10)

    def test_receive_then_transfer_then_verify_moves_inventory(self):
        self.client.login(username="web_transfer_manager", password="testpass123")
        # Create a bulk transfer of 4 units (requires TRANSFER_CREATE).
        resp = self.client.post("/transfers/create/", {
            "source_shop": self.shop1.id, "destination_shop": self.shop2.id,
            "product_id": self.product.id, "quantity": 4,
        })
        self.assertEqual(resp.status_code, 302)

        source_inv = Inventory.objects.get(shop=self.shop1, product=self.product)
        self.assertEqual(source_inv.quantity, 6)  # 10 - 4

        from stockops.models import Transfer
        transfer = Transfer.objects.latest("id")
        bulk_detail = transfer.bulk_details.first()

        # Verification requires TRANSFER_APPROVE — a different permission/role than creation,
        # matching D-08's separation of duties between the two steps.
        self.client.logout()
        self.client.login(username="web_transfer_approver", password="testpass123")
        verify_resp = self.client.post(f"/transfers/{transfer.id}/verify/", {
            f"received_{bulk_detail.id}": 4,
        })
        self.assertEqual(verify_resp.status_code, 302)
        dest_inv = Inventory.objects.get(shop=self.shop2, product=self.product)
        self.assertEqual(dest_inv.quantity, 4)

    def test_creator_without_approve_permission_cannot_verify(self):
        """The exact bug this fix addresses: a SHOP_STOCK_MANAGER (TRANSFER_CREATE only)
        should NOT be able to verify/approve a transfer — that needs TRANSFER_APPROVE."""
        self.client.login(username="web_transfer_manager", password="testpass123")
        self.client.post("/transfers/create/", {
            "source_shop": self.shop1.id, "destination_shop": self.shop2.id,
            "product_id": self.product.id, "quantity": 4,
        })
        from stockops.models import Transfer
        transfer = Transfer.objects.latest("id")

        resp = self.client.get(f"/transfers/{transfer.id}/verify/")
        self.assertEqual(resp.status_code, 302)  # redirected away, access denied

    def test_cancel_reservation_requires_post(self):
        """The fix from earlier: GET should no longer cancel a reservation."""
        from sales.models import Reservation
        customer = make_customer("web_cancel_test")
        reservation = Reservation.objects.create(user=customer, product=self.product, shop=self.shop1, status="PENDING")
        self.client.login(username="web_cancel_test", password="testpass123")

        get_resp = self.client.get(f"/my-reservations/{reservation.id}/cancel/")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "PENDING")  # GET did nothing

        post_resp = self.client.post(f"/my-reservations/{reservation.id}/cancel/")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "CANCELLED")  # POST actually cancels


class WebUserManagementTests(TestCase):
    """Tests the new user management module and role-specific dashboard content."""

    def setUp(self):
        from accounts.test_helpers import seed_roles_and_permissions
        seed_roles_and_permissions()
        self.admin = make_staff_user("web_admin", "GENERAL_ADMINISTRATOR")
        self.stockmgr = make_staff_user("web_stockmgr_nouser", "SHOP_STOCK_MANAGER")

    def test_admin_sees_user_management_nav_stockmgr_does_not(self):
        self.client.login(username="web_admin", password="testpass123")
        resp = self.client.get("/")
        self.assertContains(resp, "Utilisateurs")

        self.client.logout()
        self.client.login(username="web_stockmgr_nouser", password="testpass123")
        resp = self.client.get("/")
        self.assertNotContains(resp, "Utilisateurs")

    def test_non_admin_cannot_access_user_management(self):
        self.client.login(username="web_stockmgr_nouser", password="testpass123")
        resp = self.client.get("/utilisateurs/")
        self.assertEqual(resp.status_code, 302)  # redirected, access denied

    def test_admin_can_create_staff_user_with_role(self):
        from accounts.models import Role, User
        self.client.login(username="web_admin", password="testpass123")
        role = Role.objects.get(name="SHOP_STOCK_MANAGER")
        resp = self.client.post("/utilisateurs/create/", {
            "name": "Test Staffer", "phone": "677444444", "username": "teststaffer",
            "password": "staffpass123", "role_id": role.id,
        })
        self.assertEqual(resp.status_code, 302)
        new_user = User.objects.get(username="teststaffer")
        self.assertTrue(new_user.roles.filter(name="SHOP_STOCK_MANAGER").exists())

    def test_admin_can_grant_and_revoke_direct_permission(self):
        from accounts.models import Permission, UserPermission
        self.client.login(username="web_admin", password="testpass123")
        permission = Permission.objects.get(code="AGENT_APPROVE")

        self.client.post(f"/utilisateurs/{self.stockmgr.id}/add-permission/", {"permission_id": permission.id})
        self.assertTrue(UserPermission.objects.filter(user=self.stockmgr, permission=permission).exists())
        self.stockmgr.refresh_from_db()
        self.assertTrue(self.stockmgr.has_perm_code("AGENT_APPROVE"))

        self.client.post(f"/utilisateurs/{self.stockmgr.id}/remove-permission/{permission.id}/")
        self.assertFalse(UserPermission.objects.filter(user=self.stockmgr, permission=permission).exists())

    def test_admin_can_deactivate_user(self):
        self.client.login(username="web_admin", password="testpass123")
        resp = self.client.post(f"/utilisateurs/{self.stockmgr.id}/toggle-status/")
        self.assertEqual(resp.status_code, 302)
        self.stockmgr.refresh_from_db()
        self.assertEqual(self.stockmgr.status, "INACTIVE")


class WebRoleSpecificDashboardTests(TestCase):
    """The other half of this update: dashboards show only what each role's
    permissions actually cover, not a one-size-fits-all view."""

    def setUp(self):
        from accounts.test_helpers import seed_roles_and_permissions
        seed_roles_and_permissions()
        self.admin = make_staff_user("dash_admin", "GENERAL_ADMINISTRATOR")
        self.stockmgr = make_staff_user("dash_stockmgr", "SHOP_STOCK_MANAGER")

    def test_admin_dashboard_shows_staff_counts_not_stock_counts(self):
        self.client.login(username="dash_admin", password="testpass123")
        resp = self.client.get("/")
        self.assertContains(resp, "Utilisateurs staff")
        self.assertNotContains(resp, "Alertes stock faible")

    def test_stockmgr_dashboard_shows_stock_counts_not_staff_counts(self):
        self.client.login(username="dash_stockmgr", password="testpass123")
        resp = self.client.get("/")
        self.assertContains(resp, "Alertes stock faible")
        self.assertNotContains(resp, "Utilisateurs staff")
