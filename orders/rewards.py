from decimal import Decimal


POINTS_PER_TOMAN = Decimal("100000")


def calculate_order_reward_points(total_amount):
    """Award one point per 100,000 toman for a paid order."""
    amount = Decimal(total_amount)
    if amount <= Decimal("0.00"):
        return 0
    return max(int(amount // POINTS_PER_TOMAN), 1)
