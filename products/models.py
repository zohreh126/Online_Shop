from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(
        max_length=150,
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        allow_unicode=True,
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=("parent", "name"),
                name="unique_category_name_per_parent",
            ),
        ]

    def clean(self):
        super().clean()

        if self.pk is not None and self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "A category cannot be its own parent."}
            )

        ancestor = self.parent
        visited_ids = set()

        while ancestor:
            if ancestor.pk in visited_ids:
                break

            if ancestor.pk == self.pk:
                raise ValidationError(
                    {"parent": "Circular category relationship is not allowed."}
                )

            visited_ids.add(ancestor.pk)
            ancestor = ancestor.parent

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                self.name,
                allow_unicode=True,
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        """Keep category history while removing it from catalog navigation."""
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))



class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def in_stock(self):
        return self.active().filter(stock_quantity__gt=0)


class Product(TimeStampedModel):
    name = models.CharField(
        max_length=200,
    )

    slug = models.SlugField(
        max_length=230,
        unique=True,
        allow_unicode=True,
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )

    brand = models.CharField(
        max_length=150,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    specifications = models.JSONField(
        default=dict,
        blank=True,
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    stock_quantity = models.PositiveIntegerField(
        default=0,
    )

    image = models.ImageField(
        upload_to="products/%Y/%m/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=("is_active",)),
            models.Index(fields=("category", "is_active")),
            models.Index(fields=("sku",)),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                self.name,
                allow_unicode=True,
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def delete(self, using=None, keep_parents=False):
        """Keep catalog history while removing the product from the storefront."""
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))


class ProductReview(TimeStampedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="product_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5)),
    )
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField(max_length=1500)
    is_approved = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Product review"
        verbose_name_plural = "Product reviews"
        constraints = [
            models.UniqueConstraint(
                fields=("product", "customer"),
                condition=models.Q(is_active=True),
                name="one_active_review_per_customer_product",
            ),
        ]
        indexes = [
            models.Index(
                fields=("product", "is_active", "is_approved"),
                name="review_product_visibility_idx",
            ),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.customer.username} ({self.rating}/5)"

    def delete(self, using=None, keep_parents=False):
        """Hide a review while preserving the feedback history."""
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))


class Discount(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed amount"

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="discount",
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        help_text="Only applies to percentage discounts.",
    )

    starts_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ends_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"

    def clean(self):
        super().clean()

        if (
            self.discount_type == self.DiscountType.PERCENTAGE
            and self.value > Decimal("100.00")
        ):
            raise ValidationError(
                {"value": "Percentage discount cannot exceed 100."}
            )

        if (
            self.discount_type == self.DiscountType.FIXED
            and self.max_amount is not None
        ):
            raise ValidationError(
                {
                    "max_amount": (
                        "Maximum amount is only allowed "
                        "for percentage discounts."
                    )
                }
            )

        if (
            self.starts_at
            and self.ends_at
            and self.ends_at <= self.starts_at
        ):
            raise ValidationError(
                {"ends_at": "End date must be after start date."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_valid_now(self):
        if not self.is_active:
            return False

        now = timezone.now()

        if self.starts_at and now < self.starts_at:
            return False

        if self.ends_at and now > self.ends_at:
            return False

        return True

    def calculate_discount(self, price):
        price = Decimal(price)

        if not self.is_valid_now:
            return Decimal("0.00")

        if self.discount_type == self.DiscountType.PERCENTAGE:
            amount = price * self.value / Decimal("100")

            if self.max_amount is not None:
                amount = min(amount, self.max_amount)
        else:
            amount = self.value

        amount = min(amount, price)

        return amount.quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.product.name} - {self.value}"

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))

class DiscountCode(TimeStampedModel):
    code = models.CharField(
        max_length=50,
        unique=True,
    )

    discount_type = models.CharField(
        max_length=20,
        choices=Discount.DiscountType.choices,
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        help_text="Only applies to percentage discounts.",
    )

    minimum_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    used_count = models.PositiveIntegerField(
        default=0,
    )

    starts_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ends_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Discount code"
        verbose_name_plural = "Discount codes"
        indexes = [
            models.Index(fields=("code",)),
            models.Index(fields=("is_active",)),
        ]

    def clean(self):
        super().clean()

        if (
            self.discount_type == Discount.DiscountType.PERCENTAGE
            and self.value > Decimal("100.00")
        ):
            raise ValidationError(
                {"value": "Percentage discount cannot exceed 100."}
            )

        if (
            self.discount_type == Discount.DiscountType.FIXED
            and self.max_amount is not None
        ):
            raise ValidationError(
                {
                    "max_amount": (
                        "Maximum amount is only allowed "
                        "for percentage discounts."
                    )
                }
            )

        if (
            self.starts_at
            and self.ends_at
            and self.ends_at <= self.starts_at
        ):
            raise ValidationError(
                {"ends_at": "End date must be after start date."}
            )

        if (
            self.usage_limit is not None
            and self.used_count > self.usage_limit
        ):
            raise ValidationError(
                {"used_count": "Used count cannot exceed usage limit."}
            )

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_valid_now(self):
        if not self.is_active:
            return False

        if (
            self.usage_limit is not None
            and self.used_count >= self.usage_limit
        ):
            return False

        now = timezone.now()

        if self.starts_at and now < self.starts_at:
            return False

        if self.ends_at and now > self.ends_at:
            return False

        return True

    def calculate_discount(self, subtotal):
        subtotal = Decimal(subtotal)

        if not self.is_valid_now:
            return Decimal("0.00")

        if subtotal < self.minimum_order_amount:
            return Decimal("0.00")

        if self.discount_type == Discount.DiscountType.PERCENTAGE:
            amount = subtotal * self.value / Decimal("100")

            if self.max_amount is not None:
                amount = min(amount, self.max_amount)
        else:
            amount = self.value

        amount = min(amount, subtotal)

        return amount.quantize(Decimal("0.01"))

    def __str__(self):
        return self.code

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))
