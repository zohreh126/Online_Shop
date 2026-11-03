import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from customers.models import Customer
from products.models import DiscountCode, Product


class Cart(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(
        verbose_name=_("Session key"),
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    discount_code = models.ForeignKey(
        DiscountCode,
        verbose_name=_("Discount code"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")
        constraints = [
            models.UniqueConstraint(
                fields=("customer",),
                condition=Q(
                    customer__isnull=False,
                    is_active=True,
                ),
                name="one_active_cart_per_customer",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.customer_id and not self.session_key:
            raise ValidationError(
                "A cart must belong to a customer or session."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(
            (
                item.product.price * item.quantity
                for item in self.items.select_related("product").all()
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    def __str__(self):
        owner = self.customer or self.session_key
        return f"Cart - {owner}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(
        Cart,
        verbose_name=_("Cart"),
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=models.PROTECT,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantity"),
        validators=[
            MinValueValidator(1),
        ],
    )

    class Meta:
        ordering = ("id",)
        verbose_name = _("Cart item")
        verbose_name_plural = _("Cart items")
        constraints = [
            models.UniqueConstraint(
                fields=("cart", "product"),
                name="unique_product_per_cart",
            ),
        ]

    def clean(self):
        super().clean()

        if self.product_id and not self.product.is_active:
            raise ValidationError(
                {"product": "Inactive products cannot be added to cart."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def unit_discount(self):
        discount = getattr(self.product, "discount", None)
        if discount is None:
            return Decimal("0.00")
        return discount.calculate_discount(self.product.price)

    @property
    def unit_price(self):
        return (self.product.price - self.unit_discount).quantize(Decimal("0.01"))

    @property
    def line_total(self):
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        CONFIRMED = "confirmed", _("Confirmed")
        PROCESSING = "processing", _("Processing")
        SHIPPED = "shipped", _("Shipped")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")
        REFUNDED = "refunded", _("Refunded")

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", _("Unpaid")
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    class PaymentMethod(models.TextChoices):
        MOCK = "mock", _("Mock payment")
        CASH_ON_DELIVERY = "cash_on_delivery", _("Cash on delivery")

    class DeliveryTimeSlot(models.TextChoices):
        MORNING = "morning", _("09:00 - 12:00")
        EVENING = "evening", _("15:00 - 20:00")

    order_number = models.UUIDField(
        verbose_name=_("Order number"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    customer = models.ForeignKey(
        Customer,
        verbose_name=_("Customer"),
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        verbose_name=_("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_status = models.CharField(
        verbose_name=_("Payment status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    payment_method = models.CharField(
        verbose_name=_("Payment method"),
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MOCK,
    )
    payment_reference = models.CharField(
        verbose_name=_("Payment reference"),
        max_length=100,
        blank=True,
    )

    currency = models.CharField(
        verbose_name=_("Currency"),
        max_length=3,
        default="IRR",
    )
    subtotal = models.DecimalField(
        verbose_name=_("Subtotal"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    product_discount_amount = models.DecimalField(
        verbose_name=_("Product discount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    coupon_discount_amount = models.DecimalField(
        verbose_name=_("Coupon discount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    shipping_amount = models.DecimalField(
        verbose_name=_("Shipping amount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    total_amount = models.DecimalField(
        verbose_name=_("Total amount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    discount_code = models.ForeignKey(
        DiscountCode,
        verbose_name=_("Discount code"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    discount_code_text = models.CharField(
        verbose_name=_("Discount code text"),
        max_length=50,
        blank=True,
    )

    shipping_title = models.CharField(_("Shipping address title"), max_length=100)
    shipping_province = models.CharField(_("Shipping province"), max_length=100)
    shipping_city = models.CharField(_("Shipping city"), max_length=100)
    shipping_address_line = models.TextField(verbose_name=_("Shipping address"))
    shipping_postal_code = models.CharField(_("Shipping postal code"), max_length=10)
    shipping_recipient_name = models.CharField(_("Recipient name"), max_length=150)
    shipping_recipient_phone = models.CharField(_("Recipient phone"), max_length=20)

    delivery_date = models.DateField(
        verbose_name=_("Delivery date"),
        null=True,
        blank=True,
        help_text=_("Delivery can be scheduled from two to seven days after checkout."),
    )
    delivery_time_slot = models.CharField(
        verbose_name=_("Delivery time slot"),
        max_length=20,
        choices=DeliveryTimeSlot.choices,
        default=DeliveryTimeSlot.MORNING,
    )

    notes = models.TextField(verbose_name=_("Notes"), blank=True)
    paid_at = models.DateTimeField(verbose_name=_("Paid at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(verbose_name=_("Cancelled at"), null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        indexes = [
            models.Index(fields=("customer", "-created_at")),
            models.Index(fields=("status", "-created_at")),
            models.Index(fields=("payment_status",)),
        ]

    def clean(self):
        super().clean()

        if self.total_amount < Decimal("0.00"):
            raise ValidationError(
                {"total_amount": "Total amount cannot be negative."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.order_number)


class RewardTransaction(TimeStampedModel):
    """Immutable points earned by a customer from a completed order."""

    customer = models.ForeignKey(
        Customer,
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="reward_transactions",
    )
    order = models.OneToOneField(
        Order,
        verbose_name=_("Order"),
        on_delete=models.PROTECT,
        related_name="reward_transaction",
    )
    points = models.PositiveIntegerField(
        verbose_name=_("Points"),
        validators=[MinValueValidator(1)],
    )
    reason = models.CharField(
        verbose_name=_("Reason"),
        max_length=150,
        default="Nexora order reward",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Reward transaction")
        verbose_name_plural = _("Reward transactions")
        indexes = [
            models.Index(
                fields=("customer", "-created_at"),
                name="reward_customer_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.customer.username} +{self.points}"


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(
        Order,
        verbose_name=_("Order"),
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name = models.CharField(_("Product name"), max_length=200)
    product_sku = models.CharField(_("Product SKU"), max_length=100)
    unit_price = models.DecimalField(
        verbose_name=_("Unit price"),
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    unit_discount = models.DecimalField(
        verbose_name=_("Unit discount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantity"),
        validators=[
            MinValueValidator(1),
        ],
    )
    line_total = models.DecimalField(
        verbose_name=_("Line total"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    class Meta:
        ordering = ("id",)
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")
        constraints = [
            models.UniqueConstraint(
                fields=("order", "product"),
                name="unique_product_per_order",
            ),
        ]

    def clean(self):
        super().clean()

        if self.unit_discount > self.unit_price:
            raise ValidationError(
                {
                    "unit_discount": (
                        "Unit discount cannot exceed unit price."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.line_total = (
            (self.unit_price - self.unit_discount) * self.quantity
        ).quantize(Decimal("0.01"))

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
