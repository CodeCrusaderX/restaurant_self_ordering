from django.contrib import admin
from .models import Table, MenuCategory, MenuItem, Order, OrderItem

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("name", "token", "is_active")
    search_fields = ("name", "token")
    list_filter = ("is_active",)

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    ordering = ("sort_order", "name")

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available", "sort_order")
    list_filter = ("category", "is_available")
    search_fields = ("name",)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "table", "status", "created_at")
    list_filter = ("status", "table")
    inlines = [OrderItemInline]
    actions = ["mark_paid_verified"]

    def mark_paid_verified(self, request, queryset):
        updated = 0
        for order in queryset:
            if order.payment_reference:
                order.status = "paid"
                order.payment_id = f"MANUAL-{order.id}"
                order.save()
                updated = 1
        self.message_user(request, f"{updated} orders marked paid (verified).")
    mark_paid_verified.short_description = "Mark paid (verified txn present)"
