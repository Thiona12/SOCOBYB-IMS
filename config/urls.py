"""
config/urls.py — main URL routing, mirrors D-12's route groups.
Auth, users/me, and products are fully implemented (accounts/, catalog/).
Everything else is a permission-gated stub — see config/stub_views.py.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from .stub_views import make_stub

api_v1 = [
    # ---- Fully implemented ----
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),

    # ---- Shops (UC-03) ----
    path("shops", make_stub("USER_CREATE", "Implement Shop list/create — see D-12 §4."), name="shops"),

    # ---- Categories (UC-04) ----
    path("categories", make_stub("PRODUCT_CREATE", "Implement Category list/create — see D-12 §6."), name="categories"),

    # ---- Inventory (UC-05) ----
    path("shops/<int:shop_id>/inventory", make_stub("STOCK_VIEW", "Implement inventory view/receive — D-12 §7."), name="inventory"),
    path("shops/<int:shop_id>/inventory/receive", make_stub("STOCK_ADJUST", "BR-INV-004: log a StockMovement on every reception."), name="inventory-receive"),

    # ---- Stock Requests (UC-06) ----
    path("stock-requests", make_stub("STOCK_VIEW", "BR-REQ-001/002 — D-12 §8."), name="stock-requests"),
    path("stock-requests/<int:request_id>/approve", make_stub("TRANSFER_APPROVE", "BR-REQ-002."), name="stock-request-approve"),

    # ---- Transfers (UC-07) ----
    path("transfers", make_stub("TRANSFER_CREATE", "BR-TRF-001 — D-12 §9."), name="transfers"),
    path("transfers/<int:transfer_id>/verify", make_stub("TRANSFER_APPROVE", "BR-TRF-002: compare received identifiers, set COMPLETED_WITH_DISCREPANCY on mismatch."), name="transfer-verify"),

    # ---- Sales (UC-08) ----
    path("sales", make_stub(None, "BR-SALE-001/002 — D-12 §10. Permission resolved per-method in the real controller (STOCK_VIEW to create, REPORT_VIEW/VIEW_OWN_HISTORY to read)."), name="sales"),

    # ---- Reservations & Favorites (UC-09, UC-14) ----
    path("reservations", make_stub("RESERVATION_CREATE", "BR-RES-001/002/003 — D-12 §11."), name="reservations"),
    path("products/<int:product_id>/notify-me", make_stub("RESERVATION_CREATE", "BR-RES-002 Notify Me alert."), name="notify-me"),
    path("favorites", make_stub("FAVORITE_CREATE", "D-12 §11."), name="favorites"),

    # ---- Agents (UC-10) ----
    path("agents", make_stub("AGENT_APPROVE", "D-12 §12."), name="agents"),
    path("agents/<int:agent_id>/assignments", make_stub("AGENT_APPROVE", "BR-AGT-003: check creditLimit - outstanding >= len(stockItemIds) before creating."), name="agent-assignments"),
    path("assignment-details/<int:detail_id>/pay", make_stub("AGENT_APPROVE", "BR-AGT-004: ASSIGNED -> SOLD."), name="assignment-pay"),

    # ---- Notifications (UC-11) ----
    path("notifications/me", make_stub(None, "D-12 §13."), name="notifications-me"),

    # ---- Reporting (UC-12) ----
    path("reports/inventory", make_stub("REPORT_VIEW", "D-12 §14."), name="report-inventory"),
    path("reports/sales", make_stub("REPORT_VIEW", "D-12 §14."), name="report-sales"),
    path("reports/agents/outstanding", make_stub("REPORT_VIEW", "D-12 §14."), name="report-agents-outstanding"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", lambda request: JsonResponse({"status": "ok"})),
    path("api/v1/", include(api_v1)),
]
