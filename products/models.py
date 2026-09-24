from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=150,
    )

    slug = models.SlugField(
        verbose_name=_("Slug"),
        max_length=180,
        unique=True,
        allow_unicode=True,
    )

    parent = models.ForeignKey(
        "self",
        verbose_name=_("Parent category"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=True,
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
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
        verbose_name=_("Name"),
        max_length=200,
    )

    slug = models.SlugField(
        verbose_name=_("Slug"),
        max_length=230,
        unique=True,
        allow_unicode=True,
    )

    sku = models.CharField(
        verbose_name=_("SKU"),
        max_length=100,
        unique=True,
    )

    category = models.ForeignKey(
        Category,
        verbose_name=_("Category"),
        on_delete=models.PROTECT,
        related_name="products",
    )

    brand = models.CharField(
        verbose_name=_("Brand"),
        max_length=150,
        blank=True,
    )

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
    )

    specifications = models.JSONField(
        verbose_name=_("Specifications"),
        default=dict,
        blank=True,
    )

    price = models.DecimalField(
        verbose_name=_("Price"),
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    stock_quantity = models.PositiveIntegerField(
        verbose_name=_("Stock quantity"),
        default=0,
    )

    image = models.ImageField(
        verbose_name=_("Image"),
        upload_to="products/%Y/%m/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
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
        verbose_name=_("Product"),
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="product_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        verbose_name=_("Rating"),
        validators=(MinValueValidator(1), MaxValueValidator(5)),
    )
    title = models.CharField(_("Title"), max_length=120, blank=True)
    body = models.TextField(verbose_name=_("Comment"), max_length=1500)
    is_approved = models.BooleanField(verbose_name=_("Approved"), default=True)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Product review")
        verbose_name_plural = _("Product reviews")
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


class ProductReviewHelpfulVote(TimeStampedModel):
    review = models.ForeignKey(
        ProductReview,
        verbose_name=_("Product review"),
        on_delete=models.CASCADE,
        related_name="helpful_votes",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="review_helpful_votes",
    )

    class Meta:
        verbose_name = _("Product review helpful vote")
        verbose_name_plural = _("Product review helpful votes")
        constraints = [
            models.UniqueConstraint(
                fields=("review", "customer"),
                name="one_helpful_vote_per_customer_review",
            ),
        ]
        indexes = [
            models.Index(
                fields=("review", "created_at"),
                name="pr_helpful_review_created",
            ),
        ]

    def __str__(self):
        return f"Helpful vote - {self.review_id} / {self.customer_id}"


class ProductQuestion(TimeStampedModel):
    """A public customer question and an answer from the Nexora team."""

    product = models.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=models.PROTECT,
        related_name="questions",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="product_questions",
    )
    question = models.TextField(verbose_name=_("Question"), max_length=1000)
    answer = models.TextField(verbose_name=_("Answer"), max_length=1500, blank=True)
    answered_at = models.DateTimeField(verbose_name=_("Answered at"), null=True, blank=True)
    is_approved = models.BooleanField(verbose_name=_("Approved"), default=True)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Product question")
        verbose_name_plural = _("Product questions")
        indexes = [
            models.Index(
                fields=("product", "is_active", "is_approved"),
                name="question_product_vis_idx",
            ),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.customer.username}: {self.question[:45]}"

    def delete(self, using=None, keep_parents=False):
        """Hide a question while preserving the customer-support history."""
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))


class Discount(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", _("Percentage")
        FIXED = "fixed", _("Fixed amount")

    product = models.OneToOneField(
        Product,
        verbose_name=_("Product"),
        on_delete=models.CASCADE,
        related_name="discount",
    )

    discount_type = models.CharField(
        verbose_name=_("Discount type"),
        max_length=20,
        choices=DiscountType.choices,
    )

    value = models.DecimalField(
        verbose_name=_("Value"),
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    max_amount = models.DecimalField(
        verbose_name=_("Maximum discount"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        help_text=_("Only applies to percentage discounts."),
    )

    starts_at = models.DateTimeField(
        verbose_name=_("Starts at"),
        null=True,
        blank=True,
    )

    ends_at = models.DateTimeField(
        verbose_name=_("Ends at"),
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Discount")
        verbose_name_plural = _("Discounts")

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
    customer = models.ForeignKey(
        "customers.Customer",
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="personal_discount_codes",
        help_text=_("Leave empty for a store-wide campaign code."),
    )

    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        unique=True,
    )

    discount_type = models.CharField(
        verbose_name=_("Discount type"),
        max_length=20,
        choices=Discount.DiscountType.choices,
    )

    value = models.DecimalField(
        verbose_name=_("Value"),
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    max_amount = models.DecimalField(
        verbose_name=_("Maximum discount"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        help_text=_("Only applies to percentage discounts."),
    )

    minimum_order_amount = models.DecimalField(
        verbose_name=_("Minimum order amount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    usage_limit = models.PositiveIntegerField(
        verbose_name=_("Usage limit"),
        null=True,
        blank=True,
    )

    used_count = models.PositiveIntegerField(
        verbose_name=_("Used count"),
        default=0,
    )

    starts_at = models.DateTimeField(
        verbose_name=_("Starts at"),
        null=True,
        blank=True,
    )

    ends_at = models.DateTimeField(
        verbose_name=_("Ends at"),
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Discount code")
        verbose_name_plural = _("Discount codes")
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
