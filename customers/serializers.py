from decimal import Decimal

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from unicodedata import normalize
from rest_framework import serializers

from orders.models import RewardTransaction
from products.models import Product
from products.pricing import get_current_product_price
from products.serializers import ProductSerializer

from .jalali import normalize_jalali_date
from .models import Address, Customer, CustomerNotification, Favorite, ProductWatch, SiteFeedback


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )
    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = Customer
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
            "password",
            "password_confirm",
        )
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "phone_number": {"required": False},
            "date_of_birth": {"required": False},
        }

    def validate_username(self, value):
        value = normalize("NFC", value).strip()

        if not value:
            raise serializers.ValidationError(
                "Username cannot be empty."
            )

        return value

    def validate_email(self, value):
        return normalize("NFC", value).strip().lower()

    def validate_date_of_birth(self, value):
        try:
            return normalize_jalali_date(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        user = Customer(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
        )

        try:
            password_validation.validate_password(
                password,
                user=user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"password": list(exc.messages)}
            ) from exc

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        return Customer.objects.create_user(
            **validated_data,
        )


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
            "role",
            "is_staff",
            "is_superuser",
            "email_verified",
            "date_joined",
        )
        read_only_fields = fields


class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("username", "email", "first_name", "last_name", "phone_number", "date_of_birth")

    def validate_username(self, value):
        return normalize("NFC", value).strip()

    def validate_email(self, value):
        return normalize("NFC", value).strip().lower()

    def validate_date_of_birth(self, value):
        try:
            return normalize_jalali_date(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class CustomerNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerNotification
        fields = ("id", "kind", "title", "body", "link", "is_read", "created_at")
        read_only_fields = fields


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        customer = self.context["request"].user

        if not customer.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Current password is incorrect."}
            )

        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )

        try:
            password_validation.validate_password(
                attrs["new_password"],
                user=customer,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(exc.messages)}
            ) from exc

        return attrs

    def save(self, **kwargs):
        customer = self.context["request"].user
        customer.set_password(self.validated_data["new_password"])
        customer.save(update_fields=["password"])
        return customer


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(regex=r"^\d{6}$")

    def validate_email(self, value):
        return value.strip().lower()

class AddressSerializer(serializers.ModelSerializer):
    customer = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    class Meta:
        model = Address
        fields = (
            "id",
            "customer",
            "title",
            "province",
            "city",
            "address_line",
            "postal_code",
            "recipient_name",
            "recipient_phone",
            "is_default",
        )
        read_only_fields = ("id",)

    def validate_postal_code(self, value):
        value = (
            value.strip()
            .replace(" ", "")
            .replace("-", "")
            .translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        )

        if len(value) != 10 or not value.isdigit():
            raise serializers.ValidationError(
                "Postal code must contain exactly 10 digits."
            )

        return value

    def validate_recipient_phone(self, value):
        return (
            value.strip()
            .replace(" ", "")
            .replace("-", "")
            .translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        )

    @staticmethod
    def clear_other_defaults(customer, exclude_pk=None):
        queryset = Address.objects.filter(
            customer=customer,
            is_default=True,
        )

        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)

        queryset.update(is_default=False)

    @transaction.atomic
    def create(self, validated_data):
        customer = validated_data["customer"]

        has_existing_address = Address.objects.filter(
            customer=customer,
        ).exists()

        if not has_existing_address:
            validated_data["is_default"] = True

        if validated_data.get("is_default", False):
            self.clear_other_defaults(customer)

        return Address.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        if validated_data.get("is_default", False):
            self.clear_other_defaults(
                instance.customer,
                exclude_pk=instance.pk,
            )

        return super().update(instance, validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "product", "created_at")
        read_only_fields = fields


class FavoriteToggleSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)


class ProductWatchSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.active(),
        write_only=True,
        required=False,
    )
    current_price = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductWatch
        fields = (
            "id",
            "product",
            "product_id",
            "notify_price_drop",
            "notify_restock",
            "target_price",
            "current_price",
            "is_in_stock",
            "last_seen_price",
            "last_seen_stock_quantity",
            "last_price_notified_at",
            "last_restock_notified_at",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "product",
            "current_price",
            "is_in_stock",
            "last_seen_price",
            "last_seen_stock_quantity",
            "last_price_notified_at",
            "last_restock_notified_at",
            "is_active",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "notify_price_drop": {"required": False},
            "notify_restock": {"required": False},
            "target_price": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        product = attrs.get("product")

        if self.instance is None and product is None:
            raise serializers.ValidationError(
                {"product_id": "A product is required."}
            )

        if (
            self.instance is not None
            and product is not None
            and product.pk != self.instance.product_id
        ):
            raise serializers.ValidationError(
                {"product_id": "The watched product cannot be changed."}
            )

        target_price = attrs.get(
            "target_price",
            self.instance.target_price if self.instance else None,
        )
        if target_price is not None and target_price <= Decimal("0.00"):
            raise serializers.ValidationError(
                {"target_price": "Target price must be greater than zero."}
            )

        return attrs

    def create(self, validated_data):
        customer = self.context["request"].user
        product = validated_data.pop("product")
        current_price = get_current_product_price(product)
        defaults = {
            **validated_data,
            "last_seen_price": current_price,
            "last_seen_stock_quantity": product.stock_quantity,
            "last_price_notified_at": None,
            "last_restock_notified_at": None,
            "is_active": True,
        }
        watch, created = ProductWatch.objects.get_or_create(
            customer=customer,
            product=product,
            defaults=defaults,
        )

        if not created:
            for field in ("notify_price_drop", "notify_restock", "target_price"):
                if field in validated_data:
                    setattr(watch, field, validated_data[field])
            watch.is_active = True
            watch.last_seen_price = current_price
            watch.last_seen_stock_quantity = product.stock_quantity
            watch.last_price_notified_at = None
            watch.last_restock_notified_at = None
            watch.save(
                update_fields=(
                    "notify_price_drop",
                    "notify_restock",
                    "target_price",
                    "is_active",
                    "last_seen_price",
                    "last_seen_stock_quantity",
                    "last_price_notified_at",
                    "last_restock_notified_at",
                    "updated_at",
                )
            )

        return watch

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_current_price(self, watch):
        return get_current_product_price(watch.product)

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_in_stock(self, watch):
        return watch.product.stock_quantity > 0


class RewardTransactionSerializer(serializers.ModelSerializer):
    order_number = serializers.UUIDField(source="order.order_number", read_only=True)

    class Meta:
        model = RewardTransaction
        fields = ("id", "points", "reason", "order_number", "created_at")
        read_only_fields = fields


class RewardSummarySerializer(serializers.Serializer):
    balance = serializers.IntegerField()
    transaction_count = serializers.IntegerField()
    points_per_100000_toman = serializers.IntegerField()
    transactions = RewardTransactionSerializer(many=True)


class SiteFeedbackSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = SiteFeedback
        fields = ("id", "customer_name", "rating", "comment", "page", "created_at")
        read_only_fields = ("id", "customer_name", "created_at")
        extra_kwargs = {
            "comment": {"required": False, "allow_blank": True},
            "page": {"required": False, "allow_blank": True, "max_length": 120},
        }

    def validate_comment(self, value):
        return " ".join(value.strip().split())

    @extend_schema_field(OpenApiTypes.STR)
    def get_customer_name(self, feedback):
        if not feedback.customer_id:
            return ""
        full_name = f"{feedback.customer.first_name} {feedback.customer.last_name}".strip()
        return full_name or feedback.customer.username

    def validate_page(self, value):
        value = value.strip()
        if not value.startswith("/"):
            return ""
        return value[:120]
