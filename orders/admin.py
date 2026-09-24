from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin_permissions import RolePermissionAdminMixin

from .models import Order, OrderItem, RewardTransaction


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "product",
        "product_name",
        "product_sku",
        "unit_price",
        "unit_discount",
        "quantity",
        "line_total",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "status",
        "payment_status",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method")
    search_fields = (
        "order_number",
        "customer__username",
        "customer__email",
        "shipping_recipient_name",
        "shipping_recipient_phone",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("customer", "discount_code")
    readonly_fields = (
        "order_number",
        "customer",
        "payment_status",
        "payment_reference",
        "currency",
        "subtotal",
        "product_discount_amount",
        "coupon_discount_amount",
        "shipping_amount",
        "total_amount",
        "discount_code",
        "discount_code_text",
        "paid_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (_("Order"), {"fields": ("order_number", "customer", "status", "created_at", "updated_at")}),
        (_("Payment"), {"fields": ("payment_method", "payment_status", "payment_reference", "paid_at")}),
        (_("Totals"), {"fields": ("currency", "subtotal", "product_discount_amount", "coupon_discount_amount", "shipping_amount", "total_amount", "discount_code", "discount_code_text")}),
        (_("Shipping"), {"fields": ("shipping_title", "shipping_province", "shipping_city", "shipping_address_line", "shipping_postal_code", "shipping_recipient_name", "shipping_recipient_phone")}),
        (_("Notes"), {"fields": ("notes", "cancelled_at")}),
    )
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = ("order", "product_name", "product_sku", "quantity", "line_total")
    search_fields = ("product_name", "product_sku", "order__order_number")
    readonly_fields = (
        "order",
        "product",
        "product_name",
        "product_sku",
        "unit_price",
        "unit_discount",
        "quantity",
        "line_total",
        "created_at",
        "updated_at",
    )


@admin.register(RewardTransaction)
class RewardTransactionAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = ("customer", "order", "points", "reason", "created_at")
    search_fields = (
        "customer__username",
        "customer__email",
        "order__order_number",
        "reason",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("customer", "order")
    readonly_fields = (
        "customer",
        "order",
        "points",
        "reason",
        "created_at",
        "updated_at",
    )
