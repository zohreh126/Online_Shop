from django.contrib import admin
from django.utils import timezone

from core.admin_permissions import RolePermissionAdminMixin

from .models import (
    Category,
    Discount,
    DiscountCode,
    Product,
    ProductQuestion,
    ProductReview,
)


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


@admin.register(ProductReview)
class ProductReviewAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "product",
        "customer",
        "rating",
        "helpful_votes_count",
        "title",
        "is_approved",
        "is_active",
        "created_at",
    )
    list_filter = ("rating", "is_approved", "is_active")
    search_fields = ("product__name", "product__sku", "customer__username", "body")
    autocomplete_fields = ("product", "customer")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Helpful votes")
    def helpful_votes_count(self, review):
        return review.helpful_votes.count()


@admin.register(ProductQuestion)
class ProductQuestionAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "product",
        "customer",
        "question_preview",
        "answer_status",
        "is_approved",
        "is_active",
        "created_at",
    )
    list_filter = ("is_approved", "is_active", "answered_at")
    search_fields = (
        "product__name",
        "product__sku",
        "customer__username",
        "question",
        "answer",
    )
    autocomplete_fields = ("product", "customer")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Question")
    def question_preview(self, question):
        return question.question[:70]

    @admin.display(description="Answer")
    def answer_status(self, question):
        return "Answered" if question.answer else "Waiting"

    def save_model(self, request, obj, form, change):
        if obj.answer and obj.answered_at is None:
            obj.answered_at = timezone.now()
        super().save_model(request, obj, form, change)


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
        "customer",
        "code",
        "discount_type",
        "value",
        "minimum_order_amount",
        "used_count",
        "usage_limit",
        "is_active",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("code", "customer__username", "customer__email")
    autocomplete_fields = ("customer",)
    ordering = ("-created_at",)
    readonly_fields = ("used_count", "created_at", "updated_at")
