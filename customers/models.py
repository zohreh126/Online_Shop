from decimal import Decimal

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class CustomerManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required.")

        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)

        user = self.model(
            username=username,
            email=email,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )


class Customer(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        PRODUCT_MANAGER = "product_manager", "Product manager"
        SUPERVISOR = "supervisor", "Supervisor"
        OPERATOR = "operator", "Operator"

    username = models.CharField(
        max_length=150,
        unique=True,
    )

    email = models.EmailField(
        unique=True,
    )

    first_name = models.CharField(
        max_length=150,
        blank=True,
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        blank=True,
        default="",
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomerManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return self.username

    def delete(self, using=None, keep_parents=False):
        """Deactivate the customer instead of physically deleting the account."""
        self.is_active = False
        self.save(update_fields=("is_active",))

class Address(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    title = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address_line = models.TextField()
    postal_code = models.CharField(max_length=10)
    recipient_name = models.CharField(max_length=150)
    recipient_phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_default", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(is_default=True),
                name="one_default_address_per_customer",
            ),
        ]
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.customer.username} - {self.title}"

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.is_default = False
        self.save(update_fields=("is_active", "is_default"))


class Favorite(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="favorites",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"
        constraints = [
            models.UniqueConstraint(
                fields=("customer", "product"),
                name="unique_customer_favorite",
            ),
        ]
        indexes = [
            models.Index(
                fields=("customer", "is_active"),
                name="favorite_customer_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.customer.username} - {self.product.sku}"

    def delete(self, using=None, keep_parents=False):
        """Hide the bookmark while preserving the customer's history."""
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))


class ProductWatch(TimeStampedModel):
    """A customer's subscription to product price and availability changes."""

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="product_watches",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="product_watches",
    )
    notify_price_drop = models.BooleanField(default=True)
    notify_restock = models.BooleanField(default=True)
    target_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Optional threshold for price-drop notifications.",
    )
    last_seen_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    last_seen_stock_quantity = models.PositiveIntegerField(default=0)
    last_price_notified_at = models.DateTimeField(null=True, blank=True)
    last_restock_notified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Product watch"
        verbose_name_plural = "Product watches"
        constraints = [
            models.UniqueConstraint(
                fields=("customer", "product"),
                name="unique_customer_product_watch",
            ),
        ]
        indexes = [
            models.Index(
                fields=("customer", "is_active"),
                name="watch_customer_active_idx",
            ),
            models.Index(
                fields=("product", "is_active"),
                name="watch_product_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.customer.username} - {self.product.sku}"

    def delete(self, using=None, keep_parents=False):
        """Pause the subscription while keeping its notification history."""
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))


class SiteFeedback(TimeStampedModel):
    class Rating(models.IntegerChoices):
        VERY_BAD = 1, "Very bad"
        BAD = 2, "Bad"
        AVERAGE = 3, "Average"
        GOOD = 4, "Good"
        EXCELLENT = 5, "Excellent"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_feedback",
    )
    session_key = models.CharField(max_length=40, blank=True)
    rating = models.PositiveSmallIntegerField(choices=Rating.choices)
    comment = models.TextField(max_length=500, blank=True)
    page = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Site feedback"
        verbose_name_plural = "Site feedback"
        indexes = [
            models.Index(fields=("rating", "created_at"), name="feedback_rating_date_idx"),
            models.Index(fields=("customer", "is_active"), name="feedback_customer_active_idx"),
        ]

    def __str__(self):
        owner = self.customer.username if self.customer_id else "guest"
        return f"{owner} - {self.rating}/5"

    def delete(self, using=None, keep_parents=False):
        """Hide feedback while retaining it for product and service insights."""
        self.is_active = False
        self.save(update_fields=("is_active", "updated_at"))
