import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel
from customers.models import Customer
from products.models import DiscountCode, Product


class Cart(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    discount_code = models.ForeignKey(
        DiscountCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-updated_at",)
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
                item.line_total
                for item in self.items.select_related("product").all()
            ),
            Decimal("0.00"),
        )

    def __str__(self):
        owner = self.customer or self.session_key
        return f"Cart - {owner}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
    )

    class Meta:
        ordering = ("id",)
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
    def line_total(self):
        return (
            self.product.price * self.quantity
        ).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    class PaymentMethod(models.TextChoices):
        MOCK = "mock", "Mock payment"
        CASH_ON_DELIVERY = "cash_on_delivery", "Cash on delivery"

    order_number = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MOCK,
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        default="IRR",
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    product_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    coupon_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    shipping_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    discount_code = models.ForeignKey(
        DiscountCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    discount_code_text = models.CharField(
        max_length=50,
        blank=True,
    )

    shipping_title = models.CharField(max_length=100)
    shipping_province = models.CharField(max_length=100)
    shipping_city = models.CharField(max_length=100)
    shipping_address_line = models.TextField()
    shipping_postal_code = models.CharField(max_length=10)
    shipping_recipient_name = models.CharField(max_length=150)
    shipping_recipient_phone = models.CharField(max_length=20)

    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
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


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=100)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    unit_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    quantity = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    class Meta:
        ordering = ("id",)
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
