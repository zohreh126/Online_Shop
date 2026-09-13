from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from unicodedata import normalize
from rest_framework import serializers

from .models import Address, Customer


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
            "password",
            "password_confirm",
        )
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "phone_number": {"required": False},
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
            "role",
            "date_joined",
        )
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
