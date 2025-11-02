from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from .models import Table, MenuCategory
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from .models import Table, MenuCategory, MenuItem
from django.http import HttpResponseBadRequest
from .models import Order, OrderItem
from django.contrib import messages
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum, Count, F

def order_start(request):
    token = request.GET.get("t")
    if not token:
        return HttpResponseBadRequest("Missing table token.")
    try:
        #table = Table.finder.get(token=token)  # wrong on purpose to show diff? No. Use Table.objects
        table = Table.objects.get(token=token)
    except Exception:
        table = None
    if table is None:
        return render(request, "billingapp/token_error.html", status=404)
    request.session["table_id"] = table.id
    request.session["table_name"] = table.name
    # Lock if there's an unpaid order for this table
    unpaid = Order.objects.filter(table=table, status="pending_payment").order_by("-created_at").first()
    if unpaid:
        messages.warning(request, "You have an unpaid order. Complete payment to continue.")
        return redirect("track_order", order_id=unpaid.id)
    return redirect("customer_menu")

def customer_menu(request):
    table_name = request.session.get("table_name")
    categories = MenuCategory.objects.prefetch_related("items").all()
    return render(request, "billingapp/customer_menu.html", {
        "table_name": table_name,
        "categories": categories,
    })

@require_POST
def add_to_cart(request):
    item_id = request.POST.get("item_id")
    if not item_id:
        return HttpResponseBadRequest("Missing item id")

    cart = request.session.get("cart", {})

    cart[item_id] = cart.get(item_id, 0) + 1

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("customer_menu")

@require_POST
def update_cart(request):
    item_id = request.POST.get("item_id")
    qty = int(request.POST.get("qty", 1))

    cart = request.session.get("cart", {})

    if qty <= 0:
        cart.pop(item_id, None)
    else:
        cart[item_id] = qty

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("view_cart")

@require_POST
def remove_from_cart(request):
    item_id = request.POST.get("item_id")

    cart = request.session.get("cart", {})
    cart.pop(item_id, None)

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("view_cart")

@require_POST
def place_order(request):
    table_id = request.session.get("table_id")
    cart = request.session.get("cart", {})

    if not table_id or not cart:
        messages.error(request, "No table or empty cart.")
        return redirect("customer_menu")

    # --- Calculate total properly ---
    total = Decimal("0.00")
    for item_id, qty in cart.items():
        item = MenuItem.objects.get(id=item_id)
        total += Decimal(item.price) * int(qty)

    # --- Create order with total ---
    order = Order.objects.create(
        table_id=table_id,
        status="pending_payment",
        amount=total
    )

    # --- Create line items ---
    for item_id, qty in cart.items():
        item = MenuItem.objects.get(id=item_id)
        OrderItem.objects.create(order=order, item=item, qty=qty)

    # Clear cart
    request.session["cart"] = {}
    request.session.modified = True

    return redirect("upi_pay", order_id=order.id)


def view_cart(request):
    cart = get_cart(request)
    items = []
    total = 0

    for item_id, qty in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            line_total = item.price * qty
            items.append({"item": item, "qty": qty, "line_total": line_total})
            total += line_total
        except MenuItem.DoesNotExist:
            pass

    return render(request, "billingapp/cart.html", {"items": items, "total": total})


def get_cart(request):
    return request.session.get("cart", {})

def kitchen_dashboard(request):
    orders = Order.objects.exclude(status__in=["served", "cancelled"]).order_by("created_at")
    return render(request, "billingapp/kitchen_dashboard.html", {"orders": orders})

def update_order_status(request, order_id, new_status):
    order = get_object_or_404(Order, id=order_id)
    order.status = new_status
    order.save()
    return redirect("kitchen_dashboard")

def order_bill(request, order_id):
    order = get_object_or_404(Order.objects.select_related("table").prefetch_related("items__item"), id=order_id)
    return render(request, "billingapp/order_bill.html", {"order": order})

def track_order(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, "billingapp/track_order.html", {"order": order})

@require_POST
def cancel_order(request, order_id):
    order = Order.objects.get(id=order_id)
    
    if order.status in ["paid"]:  # only pending or paid
        order.status = "cancelled"
        order.save()
        # return to menu
        return render(request, "billingapp/order_cancelled.html")
    
    # if already accepted or preparing deny
    return HttpResponseBadRequest("Order already in kitchen, cannot cancel.")


def fake_pay(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, "billingapp/fake_pay.html", {"order": order})

@require_POST
def mark_paid(request, order_id):
    order = Order.objects.get(id=order_id)
    order.status = "paid"
    order.payment_id = f"FAKEPAY-{order.id}"
    order.save()
    return redirect("track_order", order_id=order.id)

def upi_pay(request, order_id):
    """
    Show static UPI QR image  form to submit transaction ref (manual flow).
    Place static QR image at billingapp/static/images/upi_qr.png
    """
    order = Order.objects.get(id=order_id)
    return render(request, "billingapp/upi_pay.html", {"order": order})

@require_POST
def submit_upi_txn(request, order_id):
    order = Order.objects.get(id=order_id)
    txn_ref = request.POST.get("txn_ref", "").strip()
    if not txn_ref:
        return HttpResponseBadRequest("Please enter transaction reference id")
    order.payment_reference = txn_ref
    # keep status as pending_payment until staff verifies
    order.save()
    return render(request, "billingapp/upi_submitted.html", {"order": order})

@require_POST
def verify_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Only allow verification if customer submitted UPI ref
    if not order.payment_reference:
        messages.error(request, "No payment reference yet.")
        return redirect("kitchen_dashboard")

    order.status = "paid"
    order.save()

    messages.success(request, f"Order #{order.id} marked as Paid ✅")
    return redirect("kitchen_dashboard")

def billing_dashboard(request):
    """
    Simple staff dashboard: totals by day (paidserved), filter by ?date=YYYY-MM-DD
    """
    date_str = request.GET.get("date")
    if date_str:
        day = datetime.fromisoformat(date_str).date()
    else:
        day = timezone.localdate()

    qs = Order.objects.filter(created_at__date=day, status__in=["paid", "accepted", "preparing", "served"])
    total_amount = sum(o.display_amount for o in qs)
    orders_count = qs.count()

    # top items
    top_items = (
        OrderItem.objects.filter(order__in=qs)
        .values(name=F("item__name"))
        .annotate(qty=Sum("qty"))
        .order_by("-qty")[:10]
    )

    return render(
        request,
        "billingapp/billing_dashboard.html",
        {
            "day": day,
            "orders": qs.select_related("table"),
            "total_amount": total_amount,
            "orders_count": orders_count,
            "top_items": top_items,
        },
    )

