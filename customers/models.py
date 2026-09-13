from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone


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
