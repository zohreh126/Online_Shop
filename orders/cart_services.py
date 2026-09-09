from django.db import transaction

from .models import Cart, CartItem


@transaction.atomic
def merge_guest_cart(request, customer):
    session_key = request.session.session_key
    if not session_key:
        return

    guest_cart = (
        Cart.objects.select_for_update()
        .filter(session_key=session_key, is_active=True)
        .first()
    )
    if guest_cart is None:
        return

    customer_cart, _ = Cart.objects.select_for_update().get_or_create(
        customer=customer,
        is_active=True,
    )

    guest_items = list(
        CartItem.objects.select_for_update()
        .filter(cart=guest_cart)
        .select_related("product")
    )

    for guest_item in guest_items:
        product = guest_item.product
        if not product.is_active or product.stock_quantity == 0:
            guest_item.delete()
            continue

        customer_item = (
            CartItem.objects.select_for_update()
            .filter(cart=customer_cart, product=product)
            .first()
        )
        if customer_item is None:
            guest_item.cart = customer_cart
            guest_item.quantity = min(guest_item.quantity, product.stock_quantity)
            guest_item.save(update_fields=["cart", "quantity", "updated_at"])
            continue

        customer_item.quantity = min(
            customer_item.quantity + guest_item.quantity,
            product.stock_quantity,
        )
        customer_item.save(update_fields=["quantity", "updated_at"])
        guest_item.delete()

    guest_cart.is_active = False
    guest_cart.save(update_fields=["is_active", "updated_at"])
