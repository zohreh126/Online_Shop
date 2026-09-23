from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from products.models import DiscountCode, Product

from .marketing import broadcast_store_message


@receiver(post_save, sender=Product)
def announce_new_product(sender, instance, created, **kwargs):
    if not created or not instance.is_active:
        return

    def publish():
        name = instance.name
        body = (
            f"یک محصول تازه به ویترین نکستورا اضافه شد: {name}\n\n"
            f"مشاهده محصول: /products/{instance.slug}/\n\nNexora Store"
        )
        broadcast_store_message(
            kind="product",
            title="محصول تازه در نکستورا",
            body=body,
            link=f"/products/{instance.slug}/",
            subject=f"محصول تازه نکستورا: {name}",
        )

    transaction.on_commit(publish)


@receiver(post_save, sender=DiscountCode)
def announce_global_campaign(sender, instance, created, **kwargs):
    if not created or instance.customer_id or not instance.is_active:
        return

    def publish():
        body = (
            f"یک کمپین تخفیف تازه در نکستورا فعال شد.\n"
            f"کد تخفیف: {instance.code}\n"
            f"حداقل خرید: {instance.minimum_order_amount} تومان\n\n"
            "کد را در سبد خرید وارد کن.\n\nNexora Store"
        )
        broadcast_store_message(
            kind="campaign",
            title="کمپین تخفیف تازه نکستورا",
            body=body,
            link="/#catalog",
            subject=f"کمپین تازه نکستورا؛ کد {instance.code}",
        )

    transaction.on_commit(publish)
