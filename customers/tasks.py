import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from products.pricing import get_current_product_price

from .models import Customer, ProductWatch


logger = logging.getLogger(__name__)


@shared_task
def deactivate_unverified_customers(days=3):
    cutoff = timezone.now() - timedelta(days=days)
    queryset = Customer.objects.filter(
        is_active=True,
        email_verified=False,
        is_staff=False,
        is_superuser=False,
        date_joined__lt=cutoff,
    )
    updated = queryset.update(is_active=False)
    return updated


def _watch_message(watch, events, previous_price, current_price):
    product_name = watch.product.name
    customer_name = watch.customer.first_name or watch.customer.username
    lines = [
        f"سلام {customer_name}،",
        "نکستورا برای محصولی که دنبال می‌کنی یک به‌روزرسانی دارد.",
        f"محصول: {product_name} ({watch.product.sku})",
        "",
    ]

    if "price_drop" in events:
        lines.extend(
            [
                f"کاهش قیمت: {previous_price} → {current_price} تومان",
                "Price drop: the current price is lower than the last price we recorded.",
            ]
        )

    if "restock" in events:
        lines.extend(
            [
                "موجودی محصول دوباره برقرار شده است.",
                "Back in stock: this product is available again.",
            ]
        )

    lines.extend(
        [
            "",
            "برای بررسی محصول، به فروشگاه نکستورا سر بزن.",
            "Nexora Store",
        ]
    )
    return "\n".join(lines)


@shared_task
def send_product_watch_notifications():
    """Notify active watchers when a product gets cheaper or returns to stock."""
    watch_ids = list(
        ProductWatch.objects.filter(
            is_active=True,
            customer__is_active=True,
            product__is_active=True,
        ).values_list("pk", flat=True)
    )
    checked = 0
    sent = 0
    failed = 0

    for watch_id in watch_ids:
        try:
            with transaction.atomic():
                watch = (
                    ProductWatch.objects.select_for_update()
                    .select_related("customer", "product", "product__discount")
                    .get(pk=watch_id, is_active=True)
                )
                checked += 1
                current_price = get_current_product_price(watch.product)
                previous_price = watch.last_seen_price
                previous_stock = int(watch.last_seen_stock_quantity or 0)
                price_drop = (
                    watch.notify_price_drop
                    and previous_price is not None
                    and current_price < previous_price
                    and (
                        watch.target_price is None
                        or current_price <= watch.target_price
                    )
                )
                restock = (
                    watch.notify_restock
                    and previous_stock <= 0
                    and watch.product.stock_quantity > 0
                )
                events = [
                    event
                    for event, enabled in (
                        ("price_drop", price_drop),
                        ("restock", restock),
                    )
                    if enabled
                ]

                if not events:
                    watch.last_seen_price = current_price
                    watch.last_seen_stock_quantity = watch.product.stock_quantity
                    watch.save(
                        update_fields=(
                            "last_seen_price",
                            "last_seen_stock_quantity",
                            "updated_at",
                        )
                    )
                    continue

                send_mail(
                    subject=f"Nexora alert | {watch.product.name}",
                    message=_watch_message(
                        watch,
                        events,
                        previous_price,
                        current_price,
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[watch.customer.email],
                    fail_silently=False,
                )
                now = timezone.now()
                watch.last_seen_price = current_price
                watch.last_seen_stock_quantity = watch.product.stock_quantity
                if price_drop:
                    watch.last_price_notified_at = now
                if restock:
                    watch.last_restock_notified_at = now
                watch.save(
                    update_fields=(
                        "last_seen_price",
                        "last_seen_stock_quantity",
                        "last_price_notified_at",
                        "last_restock_notified_at",
                        "updated_at",
                    )
                )
                sent += 1
        except ProductWatch.DoesNotExist:
            continue
        except Exception:
            failed += 1
            logger.exception("Product watch notification failed for watch %s", watch_id)

    return {"checked": checked, "sent": sent, "failed": failed}
