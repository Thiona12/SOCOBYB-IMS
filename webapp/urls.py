from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),
    path("", views.dashboard, name="dashboard"),

    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/receive/<int:shop_id>/", views.inventory_receive, name="inventory_receive"),

    path("transfers/", views.transfer_list, name="transfer_list"),
    path("transfers/create/", views.transfer_create, name="transfer_create"),
    path("transfers/<int:transfer_id>/verify/", views.transfer_verify, name="transfer_verify"),

    path("sales/", views.sale_list, name="sale_list"),
    path("sales/create/", views.sale_create, name="sale_create"),

    path("agents/", views.agent_list, name="agent_list"),
    path("agents/create/", views.agent_create, name="agent_create"),
    path("agents/<int:agent_id>/assign/", views.agent_assign, name="agent_assign"),

    path("catalogue/", views.catalogue, name="catalogue"),
    path("catalogue/<int:product_id>/reserve/", views.reserve_product, name="reserve_product"),
    path("catalogue/<int:product_id>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("my-reservations/", views.my_reservations, name="my_reservations"),
    path("my-reservations/<int:reservation_id>/cancel/", views.cancel_reservation, name="cancel_reservation"),
    path("my-favorites/", views.my_favorites, name="my_favorites"),
]
