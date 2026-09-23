from decimal import Decimal


FREE_SHIPPING_THRESHOLD = Decimal("2000000.00")
STANDARD_SHIPPING_FEE = Decimal("120000.00")


def calculate_shipping_amount(merchandise_total):
    """Return the transparent Nexora shipping fee for a payable cart total."""
    total = Decimal(merchandise_total or 0).quantize(Decimal("0.01"))
    if total <= Decimal("0.00") or total >= FREE_SHIPPING_THRESHOLD:
        return Decimal("0.00")
    return STANDARD_SHIPPING_FEE
