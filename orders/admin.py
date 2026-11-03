from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin_permissions import RolePermissionAdminMixin

from .models import Cart, CartItem, Order, OrderItem, RewardTransaction


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("product",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Cart)
class CartAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "cart_owner",
        "session_key",
        "item_count",
        "subtotal_display",
        "discount_code",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "customer__username",
        "customer__email",
        "session_key",
        "discount_code__code",
    )
    autocomplete_fields = ("customer", "discount_code")
    readonly_fields = ("created_at", "updated_at", "subtotal_display")
    ordering = ("-updated_at",)
    inlines = (CartItemInline,)

    @admin.display(description=_("Owner"), ordering="customer__username")
    def cart_owner(self, cart):
        return cart.customer or cart.session_key or _("Unknown")

    @admin.display(description=_("Items"))
    def item_count(self, cart):
        return cart.items.count()

    @admin.display(description=_("Subtotal"))
    def subtotal_display(self, cart):
        return cart.subtotal


@admin.register(CartItem)
class CartItemAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = ("cart", "product", "quantity", "line_total_display", "updated_at")
    search_fields = (
        "cart__customer__username",
        "cart__customer__email",
        "cart__session_key",
        "product__name",
        "product__sku",
    )
    autocomplete_fields = ("cart", "product")
    readonly_fields = ("created_at", "updated_at", "unit_discount_display", "unit_price_display", "line_total_display")
    ordering = ("-updated_at",)

    @admin.display(description=_("Unit discount"))
    def unit_discount_display(self, item):
        return item.unit_discount

    @admin.display(description=_("Unit price"))
    def unit_price_display(self, item):
        return item.unit_price

    @admin.display(description=_("Line total"))
    def line_total_display(self, item):
        return item.line_total


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
        "delivery_date",
        "delivery_time_slot",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "delivery_time_slot")
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
        (_("Shipping"), {"fields": ("shipping_title", "shipping_province", "shipping_city", "shipping_address_line", "shipping_postal_code", "shipping_recipient_name", "shipping_recipient_phone", "delivery_date", "delivery_time_slot")}),
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
