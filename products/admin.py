from django.contrib import admin

from core.admin_permissions import RolePermissionAdminMixin

from .models import Category, Discount, DiscountCode, Product


@admin.register(Category)
class CategoryAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    ordering = ("name",)
    autocomplete_fields = ("parent",)
    readonly_fields = ("slug", "created_at", "updated_at")


@admin.register(Product)
class ProductAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "brand",
        "category",
        "price",
        "stock_quantity",
        "is_active",
    )
    list_filter = ("is_active", "brand", "category")
    search_fields = ("name", "sku", "brand", "description")
    ordering = ("-created_at",)
    autocomplete_fields = ("category",)
    readonly_fields = ("slug", "created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("name", "slug", "sku", "brand", "category")}),
        ("Catalog content", {"fields": ("description", "specifications", "image")}),
        ("Pricing and inventory", {"fields": ("price", "stock_quantity", "is_active")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Discount)
class DiscountAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "product",
        "discount_type",
        "value",
        "is_active",
        "starts_at",
        "ends_at",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("product__name", "product__sku")
    autocomplete_fields = ("product",)
    ordering = ("-created_at",)


@admin.register(DiscountCode)
class DiscountCodeAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "value",
        "minimum_order_amount",
        "used_count",
        "usage_limit",
        "is_active",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)
    ordering = ("-created_at",)
    readonly_fields = ("used_count", "created_at", "updated_at")
