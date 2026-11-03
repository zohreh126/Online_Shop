from decimal import Decimal

from .models import Discount


def get_current_product_price(product):
    """Return the same effective price that the storefront exposes."""
    base_price = Decimal(product.price)

    try:
        discount = product.discount
    except Discount.DoesNotExist:
        return base_price

    discount_amount = discount.calculate_discount(base_price)
    return max(base_price - discount_amount, Decimal("0.00"))
