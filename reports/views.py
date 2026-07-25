"""
Reporting endpoints — D-12 §14, all REPORT_VIEW.
Deliberately simple aggregate queries; the reporting NFR (D-10 §3) still
needs dashboard/UI design, but the underlying data queries are real.
"""
from django.db.models import Sum, Count, F
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import HasPermission
from inventory.models import Inventory, StockItem
from sales.models import Sale
from stockops.models import Transfer
from agents.models import AssignmentDetail


class InventoryReportView(APIView):
    permission_classes = [HasPermission("REPORT_VIEW")]

    def get(self, request):
        low_stock = Inventory.objects.filter(quantity__lte=F("minimum_level")).select_related("shop", "product")
        data = [
            {"shopId": i.shop_id, "productId": i.product_id, "quantity": i.quantity, "minimumLevel": i.minimum_level}
            for i in low_stock
        ]
        return Response({"lowStockAlerts": data, "totalTrackedItems": StockItem.objects.count()})


class SalesReportView(APIView):
    permission_classes = [HasPermission("REPORT_VIEW")]

    def get(self, request):
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        shop_id = request.query_params.get("shopId")

        qs = Sale.objects.all()
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        if shop_id:
            qs = qs.filter(shop_id=shop_id)

        summary = qs.aggregate(totalSales=Count("id"), totalRevenue=Sum("total_amount"))
        return Response(summary)


class TransfersReportView(APIView):
    permission_classes = [HasPermission("REPORT_VIEW")]

    def get(self, request):
        by_status = Transfer.objects.values("status").annotate(count=Count("id"))
        return Response({"byStatus": list(by_status)})


class AgentsOutstandingReportView(APIView):
    permission_classes = [HasPermission("REPORT_VIEW")]

    def get(self, request):
        outstanding = (
            AssignmentDetail.objects.filter(payment_status="UNPAID")
            .values("assignment__agent_id", "assignment__agent__name")
            .annotate(outstandingCount=Count("id"))
        )
        return Response({"data": list(outstanding)})
