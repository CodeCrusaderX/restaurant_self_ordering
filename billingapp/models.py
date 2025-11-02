from django.db import models

from django.db import models
from django.utils import timezone
import secrets

class Table(models.Model):
    name = models.CharField(max_length=50, unique=True)
    token = models.CharField(max_length=24, unique=True, editable=False, db_index=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(9)[:24]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"

class MenuCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("category", "name")
        ordering = ["category__sort_order", "category__name", "sort_order", "name"]

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending_payment", "Pending Payment"),
        ("paid", "Paid"),
        ("accepted", "Accepted by Kitchen"),
        ("preparing", "Preparing"),
        ("served", "Served"),
        ("cancelled", "Cancelled"),
    ]
    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_payment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_id = models.CharField(max_length=200, blank=True)  # gateway id later
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, default=None, null=True,unique=True)
    
    # ---- helpers (no DB change) ----
    @property
    def subtotal(self):
        from decimal import Decimal
        total = Decimal("0.00")
        for li in self.items.select_related("item").all():
            total += (li.item.price * li.qty)
        return total

    @property
    def display_amount(self):
        """Prefer computed subtotal; fall back to stored amount."""
        return self.subtotal if self.amount is None else self.amount

    def __str__(self):
        return f"Order #{self.pk} - {self.table.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("order", "item")

    def line_total(self):
        return self.item.price * self.qty

