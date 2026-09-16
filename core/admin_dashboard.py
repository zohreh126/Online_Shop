from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils import timezone

from customers.models import Customer
from orders.models import Order
from products.models import Discount, Product, ProductReview


def _fa_number(value):
    translation = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(value).translate(translation)


def _fa_money(value):
    amount = int(value or 0)
    return f"{_fa_number(f'{amount:,}'.replace(',', '٬'))} تومان"


def _can_access(user, app_label, model_name):
    return user.is_superuser or any(
        user.has_perm(f"{app_label}.{action}_{model_name}")
        for action in ("view", "change", "add", "delete")
    )


@staff_member_required
def nexora_admin_index(request):
    """Render a data-rich home for the existing Django admin site."""
    context = admin.site.each_context(request)
    context.update(
        {
            "title": admin.site.index_title,
            "subtitle": None,
            "app_list": admin.site.get_app_list(request),
            "nexora_metrics": [],
            "nexora_recent_orders": [],
            "nexora_recent_reviews": [],
        }
    )

    user = request.user
    metrics = []

    if _can_access(user, "products", "product"):
        metrics.append(
            {
                "icon": "◈",
                "label": "محصولات فعال",
                "value": _fa_number(Product.objects.filter(is_active=True).count()),
                "hint": "در ویترین فروشگاه",
                "url": "admin:products_product_changelist",
                "tone": "purple",
            }
        )

    if _can_access(user, "products", "discount"):
        now = timezone.now()
        active_discount_filter = (
            Q(is_active=True)
            & (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
            & (Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        )
        discounted_products = Product.objects.filter(
            is_active=True,
            discount__in=Discount.objects.filter(active_discount_filter),
        ).count()
        metrics.append(
            {
                "icon": "%",
                "label": "محصولات تخفیف‌دار",
                "value": _fa_number(discounted_products),
                "hint": "کمپین‌های فعال امروز",
                "url": "admin:products_discount_changelist",
                "tone": "coral",
            }
        )

    if _can_access(user, "orders", "order"):
        order_queryset = Order.objects.all()
        pending_count = order_queryset.filter(
            status__in=(
                Order.Status.PENDING,
                Order.Status.CONFIRMED,
                Order.Status.PROCESSING,
            )
        ).count()
        revenue = order_queryset.filter(
            payment_status=Order.PaymentStatus.PAID,
        ).aggregate(total=Sum("total_amount"))["total"]
        metrics.append(
            {
                "icon": "▣",
                "label": "سفارش‌ها",
                "value": _fa_number(order_queryset.count()),
                "hint": f"{_fa_number(pending_count)} در حال پیگیری",
                "url": "admin:orders_order_changelist",
                "tone": "green",
            }
        )
        metrics.append(
            {
                "icon": "↗",
                "label": "فروش پرداخت‌شده",
                "value": _fa_money(revenue),
                "hint": "جمع سفارش‌های موفق",
                "url": "admin:orders_order_changelist",
                "tone": "gold",
            }
        )
        context["nexora_recent_orders"] = (
            order_queryset.select_related("customer").order_by("-created_at")[:5]
        )

    if _can_access(user, "customers", "customer"):
        metrics.append(
            {
                "icon": "♙",
                "label": "مشتری‌های فعال",
                "value": _fa_number(
                    Customer.objects.filter(is_active=True, is_staff=False).count()
                ),
                "hint": "حساب‌های مشتری فروشگاه",
                "url": "admin:customers_customer_changelist",
                "tone": "blue",
            }
        )

    if _can_access(user, "products", "productreview"):
        metrics.append(
            {
                "icon": "★",
                "label": "نظرهای منتشرشده",
                "value": _fa_number(
                    ProductReview.objects.filter(
                        is_active=True,
                        is_approved=True,
                    ).count()
                ),
                "hint": "بازخورد قابل نمایش در فروشگاه",
                "url": "admin:products_productreview_changelist",
                "tone": "mint",
            }
        )
        context["nexora_recent_reviews"] = (
            ProductReview.objects.filter(
                is_active=True,
            )
            .select_related("product", "customer")
            .order_by("-created_at")[:5]
        )

    context["nexora_metrics"] = metrics
    return render(request, "admin/index.html", context)
