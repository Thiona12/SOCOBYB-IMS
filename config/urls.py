"""
config/urls.py — main URL routing, mirrors D-12's route groups.
All routes are now fully implemented (see README for what changed since the
stub-scaffold version).
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from accounts.shop_views import ShopListCreateView, ShopDetailView
from catalog.category_views import CategoryListCreateView
from inventory.views import ShopInventoryView, ReceiveInventoryView, StockItemMovementsView
from stockops.views import (
    StockRequestListCreateView, StockRequestApproveView, StockRequestRejectView,
    TransferCreateView, TransferShipView, TransferVerifyView, TransferDetailView,
)
from sales.views import (
    SaleListCreateView, SaleDetailView, ReservationCreateView, MyReservationsView,
    ReservationCancelView, FavoriteCreateView, MyFavoritesView, FavoriteDeleteView,
)
from agents.views import AgentListCreateView, AgentApproveView, AgentAssignmentsView, AssignmentDetailPayView
from notifications.views import MyNotificationsView, NotificationReadView
from reports.views import InventoryReportView, SalesReportView, TransfersReportView, AgentsOutstandingReportView

api_v1 = [
    # ---- Auth & Users ----
    path("", include("accounts.urls")),

    # ---- Products (catalog) ----
    path("", include("catalog.urls")),

    # ---- Shops (UC-03) ----
    path("shops", ShopListCreateView.as_view(), name="shops"),
    path("shops/<int:shop_id>", ShopDetailView.as_view(), name="shop-detail"),

    # ---- Categories (UC-04) ----
    path("categories", CategoryListCreateView.as_view(), name="categories"),

    # ---- Inventory (UC-05) ----
    path("shops/<int:shop_id>/inventory", ShopInventoryView.as_view(), name="inventory"),
    path("shops/<int:shop_id>/inventory/receive", ReceiveInventoryView.as_view(), name="inventory-receive"),
    path("stock-items/<int:stock_item_id>/movements", StockItemMovementsView.as_view(), name="stock-item-movements"),

    # ---- Stock Requests (UC-06) ----
    path("stock-requests", StockRequestListCreateView.as_view(), name="stock-requests"),
    path("stock-requests/<int:request_id>/approve", StockRequestApproveView.as_view(), name="stock-request-approve"),
    path("stock-requests/<int:request_id>/reject", StockRequestRejectView.as_view(), name="stock-request-reject"),

    # ---- Transfers (UC-07) ----
    path("transfers", TransferCreateView.as_view(), name="transfers"),
    path("transfers/<int:transfer_id>", TransferDetailView.as_view(), name="transfer-detail"),
    path("transfers/<int:transfer_id>/ship", TransferShipView.as_view(), name="transfer-ship"),
    path("transfers/<int:transfer_id>/verify", TransferVerifyView.as_view(), name="transfer-verify"),

    # ---- Sales (UC-08) ----
    path("sales", SaleListCreateView.as_view(), name="sales"),
    path("sales/<int:sale_id>", SaleDetailView.as_view(), name="sale-detail"),

    # ---- Reservations & Favorites (UC-09, UC-14) ----
    path("reservations", ReservationCreateView.as_view(), name="reservations"),
    path("reservations/me", MyReservationsView.as_view(), name="reservations-me"),
    path("reservations/<int:reservation_id>/cancel", ReservationCancelView.as_view(), name="reservation-cancel"),
    path("favorites", FavoriteCreateView.as_view(), name="favorites"),
    path("favorites/me", MyFavoritesView.as_view(), name="favorites-me"),
    path("favorites/<int:favorite_id>", FavoriteDeleteView.as_view(), name="favorite-delete"),

    # ---- Agents (UC-10) ----
    path("agents", AgentListCreateView.as_view(), name="agents"),
    path("agents/<int:agent_id>/approve", AgentApproveView.as_view(), name="agent-approve"),
    path("agents/<int:agent_id>/assignments", AgentAssignmentsView.as_view(), name="agent-assignments"),
    path("assignment-details/<int:detail_id>/pay", AssignmentDetailPayView.as_view(), name="assignment-pay"),

    # ---- Notifications (UC-11) ----
    path("notifications/me", MyNotificationsView.as_view(), name="notifications-me"),
    path("notifications/<int:notification_id>/read", NotificationReadView.as_view(), name="notification-read"),

    # ---- Reporting (UC-12) ----
    path("reports/inventory", InventoryReportView.as_view(), name="report-inventory"),
    path("reports/sales", SalesReportView.as_view(), name="report-sales"),
    path("reports/transfers", TransfersReportView.as_view(), name="report-transfers"),
    path("reports/agents/outstanding", AgentsOutstandingReportView.as_view(), name="report-agents-outstanding"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", lambda request: JsonResponse({"status": "ok"})),
    path("api/v1/", include(api_v1)),
]
