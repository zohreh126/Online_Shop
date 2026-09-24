from decimal import Decimal

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class CustomerManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required.")

        if not email:
            raise ValueError("Email is required.")

        username = self.model.normalize_username(str(username).strip())
        email = self.normalize_email(email).strip().lower()

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
        PRODUCT_MANAGER = "product_manager", _("Product manager")
        SUPERVISOR = "supervisor", _("Supervisor")
        OPERATOR = "operator", _("Operator")

    username = models.CharField(
        verbose_name=_("Username"),
        max_length=150,
    )

    email = models.EmailField(
        verbose_name=_("Email address"),
    )

    first_name = models.CharField(
        verbose_name=_("First name"),
        max_length=150,
        blank=True,
    )

    last_name = models.CharField(
        verbose_name=_("Last name"),
        max_length=150,
        blank=True,
    )

    phone_number = models.CharField(
        verbose_name=_("Phone number"),
        max_length=20,
        blank=True,
    )

    role = models.CharField(
        verbose_name=_("Role"),
        max_length=30,
        choices=Role.choices,
        blank=True,
        default="",
    )

    is_staff = models.BooleanField(verbose_name=_("Staff status"), default=False)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)
    email_verified = models.BooleanField(verbose_name=_("Email verified"), default=False)

    date_of_birth = models.CharField(
        verbose_name=_("Date of birth"),
        max_length=10,
        blank=True,
        help_text=_("Jalali date in YYYY/MM/DD format."),
    )

    date_joined = models.DateTimeField(
        verbose_name=_("Date joined"),
        default=timezone.now,
    )

    objects = CustomerManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                condition=models.Q(is_active=True),
                name="unique_active_customer_username",
            ),
            models.UniqueConstraint(
                Lower("email"),
                condition=models.Q(is_active=True),
                name="unique_active_customer_email",
            ),
        ]

    def __str__(self):
        return self.username

    def delete(self, using=None, keep_parents=False):
        """Deactivate the customer instead of physically deleting the account."""
        self.is_active = False
        update_fields = ["is_active"]
        if not self.is_superuser:
            self.is_staff = False
            self.role = ""
            update_fields.extend(("is_staff", "role"))
        self.save(update_fields=update_fields)

class Address(models.Model):
    customer = models.ForeignKey(
        Customer,
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    title = models.CharField(_("Title"), max_length=100)
    province = models.CharField(_("Province"), max_length=100)
    city = models.CharField(_("City"), max_length=100)
    address_line = models.TextField(verbose_name=_("Address"))
    postal_code = models.CharField(_("Postal code"), max_length=10)
    recipient_name = models.CharField(_("Recipient name"), max_length=150)
    recipient_phone = models.CharField(_("Recipient phone"), max_length=20)
    is_default = models.BooleanField(verbose_name=_("Default address"), default=False)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    class Meta:
        ordering = ["-is_default", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(is_default=True),
                name="one_default_address_per_customer",
            ),
        ]
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self):
        return f"{self.customer.username} - {self.title}"

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.is_default = False
        self.save(update_fields=("is_active", "is_default"))


class Favorite(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    product = models.ForeignKey(
        "products.Product",
        verbose_name=_("Product"),
        on_delete=models.PROTECT,
        related_name="favorites",
    )
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Favorite")
        verbose_name_plural = _("Favorites")
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
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="product_watches",
    )
    product = models.ForeignKey(
        "products.Product",
        verbose_name=_("Product"),
        on_delete=models.PROTECT,
        related_name="product_watches",
    )
    notify_price_drop = models.BooleanField(verbose_name=_("Notify on price drop"), default=True)
    notify_restock = models.BooleanField(verbose_name=_("Notify on restock"), default=True)
    target_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Target price"),
        help_text=_("Optional threshold for price-drop notifications."),
    )
    last_seen_price = models.DecimalField(
        verbose_name=_("Last seen price"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    last_seen_stock_quantity = models.PositiveIntegerField(verbose_name=_("Last seen stock quantity"), default=0)
    last_price_notified_at = models.DateTimeField(verbose_name=_("Last price notification"), null=True, blank=True)
    last_restock_notified_at = models.DateTimeField(verbose_name=_("Last restock notification"), null=True, blank=True)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Product watch")
        verbose_name_plural = _("Product watches")
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
        VERY_BAD = 1, _("Very bad")
        BAD = 2, _("Bad")
        AVERAGE = 3, _("Average")
        GOOD = 4, _("Good")
        EXCELLENT = 5, _("Excellent")

    customer = models.ForeignKey(
        Customer,
        verbose_name=_("Customer"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_feedback",
    )
    session_key = models.CharField(verbose_name=_("Session key"), max_length=40, blank=True)
    rating = models.PositiveSmallIntegerField(verbose_name=_("Rating"), choices=Rating.choices)
    comment = models.TextField(verbose_name=_("Comment"), max_length=500, blank=True)
    page = models.CharField(verbose_name=_("Page"), max_length=120, blank=True)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Site feedback")
        verbose_name_plural = _("Site feedback")
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


class CustomerNotification(TimeStampedModel):
    class Kind(models.TextChoices):
        PRODUCT = "product", _("New product")
        CAMPAIGN = "campaign", _("Store campaign")
        BIRTHDAY = "birthday", _("Birthday reward")
        SYSTEM = "system", _("Account update")

    customer = models.ForeignKey(
        Customer,
        verbose_name=_("Customer"),
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(verbose_name=_("Type"), max_length=20, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField(verbose_name=_("Title"), max_length=180)
    body = models.TextField(verbose_name=_("Message"), max_length=1200)
    link = models.CharField(verbose_name=_("Link"), max_length=255, blank=True)
    is_read = models.BooleanField(verbose_name=_("Read"), default=False)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Customer notification")
        verbose_name_plural = _("Customer notifications")
        indexes = [
            models.Index(fields=("customer", "is_read", "created_at"), name="notif_customer_read_idx"),
        ]

    def __str__(self):
        return f"{self.customer.username} - {self.title}"
