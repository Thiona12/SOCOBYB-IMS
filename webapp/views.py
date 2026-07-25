"""
webapp/views.py — session-based Django template frontend.
Reuses the same models and business rules as the DRF API (D-12), just
rendered as server-side HTML instead of JSON, for people who'd rather work
with Django templates than a separate React app.
"""
from decimal import Decimal
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import time

from accounts.models import User, Role, UserRole, Shop
from catalog.models import Category, Product
from inventory.models import Inventory, StockItem, StockMovement
from sales.models import Sale, SaleDetail, Reservation, Favorite
from agents.models import Agent, Assignment, AssignmentDetail
from stockops.models import StockRequest, Transfer, TransferDetail, TransferBulkDetail


def is_customer(user):
    return user.roles.count() == 1 and user.roles.filter(name="CUSTOMER").exists()


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        if User.objects.filter(username=username).exists():
            return render(request, "webapp/register.html", {"error": "Nom d'utilisateur déjà utilisé."})

        user_number = f"CUST-{str(int(time.time()))[-6:]}"
        user = User.objects.create_user(
            username=username,
            name=request.POST.get("name", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            password=request.POST.get("password"),
            user_number=user_number,
        )
        customer_role, _ = Role.objects.get_or_create(name="CUSTOMER")
        UserRole.objects.get_or_create(user=user, role=customer_role)
        auth_login(request, user)
        messages.success(request, "Bienvenue ! Votre compte a été créé.")
        return redirect("dashboard")

    return render(request, "webapp/register.html")


@login_required
def dashboard(request):
    if is_customer(request.user):
        return redirect("catalogue")

    context = {
        "is_customer": False,
        "shop_count": Shop.objects.count(),
        "product_count": Product.objects.count(),
        "pending_requests": StockRequest.objects.filter(status="PENDING").count(),
        "pending_transfers": Transfer.objects.filter(status__in=["PENDING", "IN_TRANSIT"]).count(),
        "low_stock": Inventory.objects.filter(quantity__lte=1).count(),
    }
    return render(request, "webapp/dashboard.html", context)


# ---- Inventory ----

@login_required
def inventory_list(request):
    if is_customer(request.user):
        return redirect("catalogue")
    shops = Shop.objects.all()
    selected_shop_id = request.GET.get("shop", shops.first().id if shops.exists() else None)
    inventories = Inventory.objects.filter(shop_id=selected_shop_id).select_related("product") if selected_shop_id else []
    products = Product.objects.filter(status="ACTIVE")
    return render(request, "webapp/inventory_list.html", {
        "is_customer": False, "shops": shops, "selected_shop_id": int(selected_shop_id) if selected_shop_id else None,
        "inventories": inventories, "products": products,
    })


@login_required
def inventory_receive(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    if request.method == "POST":
        product = get_object_or_404(Product, id=request.POST.get("product_id"))
        quantity = int(request.POST.get("quantity"))
        identifiers_raw = request.POST.get("identifiers", "").strip()
        identifiers = [i.strip() for i in identifiers_raw.split(",") if i.strip()] if identifiers_raw else []

        inventory, _ = Inventory.objects.get_or_create(shop=shop, product=product)
        if identifiers:
            for identifier in identifiers:
                item = StockItem.objects.create(product=product, identifier=identifier, identifier_type="IMEI", status="AVAILABLE")
                StockMovement.objects.create(stock_item=item, movement_type="RECEPTION", reference_id=shop.id)
            inventory.quantity += len(identifiers)
        else:
            inventory.quantity += quantity
        inventory.save()
        messages.success(request, f"Stock reçu : {quantity} x {product.name} à {shop.name}.")
        return redirect(f"/inventory/?shop={shop.id}")
    return redirect("inventory_list")


# ---- Transfers ----

@login_required
def transfer_list(request):
    transfers = Transfer.objects.select_related("source_shop", "destination_shop").order_by("-date")
    return render(request, "webapp/transfer_list.html", {"is_customer": False, "transfers": transfers, "shops": Shop.objects.all()})


@login_required
def transfer_create(request):
    if request.method == "POST":
        source = get_object_or_404(Shop, id=request.POST.get("source_shop"))
        destination = get_object_or_404(Shop, id=request.POST.get("destination_shop"))
        product = get_object_or_404(Product, id=request.POST.get("product_id"))
        quantity = int(request.POST.get("quantity"))

        if source.id == destination.id:
            messages.error(request, "La boutique source et destination doivent être différentes.")
            return redirect("transfer_list")

        inv = Inventory.objects.filter(shop=source, product=product).first()
        if not inv or inv.quantity < quantity:
            messages.error(request, f"Stock insuffisant pour {product.name} à {source.name}.")
            return redirect("transfer_list")

        with transaction.atomic():
            inv.quantity -= quantity
            inv.save()
            transfer = Transfer.objects.create(source_shop=source, destination_shop=destination, status="PENDING")
            TransferBulkDetail.objects.create(transfer=transfer, product=product, shipped_quantity=quantity, verification_status="PENDING")

        messages.success(request, f"Transfert #{transfer.id} créé : {quantity} x {product.name}.")
        return redirect("transfer_list")
    return redirect("transfer_list")


@login_required
def transfer_verify(request, transfer_id):
    transfer = get_object_or_404(Transfer, id=transfer_id)
    if request.method == "POST":
        has_discrepancy = False
        for bulk_detail in transfer.bulk_details.all():
            received = int(request.POST.get(f"received_{bulk_detail.id}", 0))
            bulk_detail.received_quantity = received
            if received != bulk_detail.shipped_quantity:
                has_discrepancy = True
                bulk_detail.verification_status = "DISCREPANCY"
            else:
                bulk_detail.verification_status = "MATCHED"
            bulk_detail.save()
            if received > 0:
                dest_inv, _ = Inventory.objects.get_or_create(shop=transfer.destination_shop, product=bulk_detail.product)
                dest_inv.quantity += received
                dest_inv.save()

        for detail in transfer.details.select_related("stock_item"):
            received_ids = request.POST.getlist("received_identifiers")
            if detail.stock_item.identifier in received_ids:
                detail.verification_status = "MATCHED"
                detail.stock_item.status = "AVAILABLE"
            else:
                has_discrepancy = True
                detail.verification_status = "DISCREPANCY"
            detail.save()
            detail.stock_item.save()

        transfer.status = "COMPLETED_WITH_DISCREPANCY" if has_discrepancy else "COMPLETED"
        transfer.save()
        messages.success(request, f"Transfert #{transfer.id} : {transfer.status}")
        return redirect("transfer_list")

    return render(request, "webapp/transfer_verify.html", {"is_customer": False, "transfer": transfer})


# ---- Sales ----

@login_required
def sale_list(request):
    sales = Sale.objects.select_related("shop", "user").order_by("-date")[:50]
    return render(request, "webapp/sale_list.html", {
        "is_customer": False, "sales": sales, "shops": Shop.objects.all(),
        "products": Product.objects.filter(status="ACTIVE"),
    })


@login_required
def sale_create(request):
    if request.method == "POST":
        shop = get_object_or_404(Shop, id=request.POST.get("shop_id"))
        product = get_object_or_404(Product, id=request.POST.get("product_id"))
        quantity = int(request.POST.get("quantity"))
        customer_username = request.POST.get("customer_username", "").strip()

        customer = User.objects.filter(username=customer_username).first() if customer_username else request.user
        if not customer:
            messages.error(request, "Client introuvable.")
            return redirect("sale_list")

        inv = Inventory.objects.filter(shop=shop, product=product).first()
        if not inv or inv.quantity < quantity:
            messages.error(request, f"Stock insuffisant pour {product.name}.")
            return redirect("sale_list")

        with transaction.atomic():
            inv.quantity -= quantity
            inv.save()
            total = product.selling_price * quantity
            sale = Sale.objects.create(
                shop=shop, user=customer, total_amount=total,
                customer_mtn_number=request.POST.get("customer_mtn_number") or None,
                device_mtn_number=request.POST.get("device_mtn_number") or None,
            )
            SaleDetail.objects.create(sale=sale, product=product, quantity=quantity, price=product.selling_price)
            Reservation.objects.filter(user=customer, product=product, status="PENDING").update(status="CONVERTED")

        messages.success(request, f"Vente #{sale.id} enregistrée : {total} FCFA.")
        return redirect("sale_list")
    return redirect("sale_list")


# ---- Agents ----

@login_required
def agent_list(request):
    agents = Agent.objects.all()
    return render(request, "webapp/agent_list.html", {"is_customer": False, "agents": agents})


@login_required
def agent_create(request):
    if request.method == "POST":
        Agent.objects.create(
            name=request.POST.get("name"), phone=request.POST.get("phone"),
            credit_limit=Decimal(request.POST.get("credit_limit", "0")), status="PENDING",
        )
        messages.success(request, "Agent créé.")
    return redirect("agent_list")


@login_required
def agent_assign(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    if request.method == "POST":
        raw_ids = request.POST.get("stock_item_ids", "")
        stock_item_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip()]
        outstanding = AssignmentDetail.objects.filter(assignment__agent=agent, payment_status="UNPAID").count()

        if outstanding + len(stock_item_ids) > agent.credit_limit:
            messages.error(request, f"Plafond de crédit dépassé : {outstanding} en cours, limite {agent.credit_limit}.")
            return redirect("agent_list")

        with transaction.atomic():
            assignment = Assignment.objects.create(agent=agent, status="ACTIVE")
            for item_id in stock_item_ids:
                item = get_object_or_404(StockItem, id=item_id, status="AVAILABLE")
                item.status = "ASSIGNED"
                item.save()
                AssignmentDetail.objects.create(assignment=assignment, stock_item=item, payment_status="UNPAID")
        messages.success(request, f"{len(stock_item_ids)} produit(s) affecté(s) à {agent.name}.")
    return redirect("agent_list")


# ---- Customer: catalogue, reservations, favorites ----

@login_required
def catalogue(request):
    products = Product.objects.filter(status="ACTIVE").select_related("category")
    favorite_ids = set(Favorite.objects.filter(user=request.user).values_list("product_id", flat=True))
    return render(request, "webapp/catalogue.html", {
        "is_customer": True, "products": products, "favorite_ids": favorite_ids, "shops": Shop.objects.all(),
    })


@login_required
def reserve_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    shop_id = request.POST.get("shop_id")
    shop = get_object_or_404(Shop, id=shop_id)
    Reservation.objects.create(user=request.user, product=product, shop=shop, status="PENDING")
    messages.success(request, f"{product.name} réservé.")
    return redirect("catalogue")


@login_required
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    favorite = Favorite.objects.filter(user=request.user, product=product).first()
    if favorite:
        favorite.delete()
        messages.info(request, f"{product.name} retiré des favoris.")
    else:
        Favorite.objects.create(user=request.user, product=product)
        messages.success(request, f"{product.name} ajouté aux favoris.")
    return redirect("catalogue")


@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(user=request.user).select_related("product", "shop").order_by("-created_date")
    return render(request, "webapp/my_reservations.html", {"is_customer": True, "reservations": reservations})


@login_required
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    reservation.status = "CANCELLED"
    reservation.save()
    messages.info(request, "Réservation annulée.")
    return redirect("my_reservations")


@login_required
def my_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related("product")
    return render(request, "webapp/my_favorites.html", {"is_customer": True, "favorites": favorites})
