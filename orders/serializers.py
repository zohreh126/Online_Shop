from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from customers.models import Address
from products.models import DiscountCode, Product
from products.serializers import ProductSerializer

from .models import Cart, CartItem, Order, OrderItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.active(),
        write_only=True,
        required=False,
    )

    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "product_id",
            "quantity",
            "line_total",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "product",
            "line_total",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        product = attrs.get("product")

        if self.instance is not None:
            current_product = self.instance.product

            if product is not None and product.pk != current_product.pk:
                raise serializers.ValidationError(
                    {
                        "product_id": (
                            "Changing the product of a cart item "
                            "is not allowed."
                        )
                    }
                )

            product = current_product

        if product is None:
            raise serializers.ValidationError(
                {
                    "product_id": (
                        "This field is required when adding an item."
                    )
                }
            )

        if not product.is_active:
            raise serializers.ValidationError(
                {
                    "product_id": (
                        "Inactive products cannot be added to cart."
                    )
                }
            )

        quantity = attrs.get(
            "quantity",
            self.instance.quantity if self.instance else None,
        )

        if quantity is not None and quantity > product.stock_quantity:
            raise serializers.ValidationError(
                {
                    "quantity": (
                        "Requested quantity exceeds available stock."
                    )
                }
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        cart = validated_data.pop("cart", None)

        if cart is None:
            cart = self.context.get("cart")

        if cart is None:
            raise serializers.ValidationError(
                "A cart is required."
            )

        product = validated_data.pop("product")
        quantity = validated_data["quantity"]

        existing_item = (
            CartItem.objects.select_for_update()
            .filter(
                cart=cart,
                product=product,
            )
            .first()
        )

        if existing_item is not None:
            new_quantity = existing_item.quantity + quantity

            if new_quantity > product.stock_quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Requested quantity exceeds available stock."
                        )
                    }
                )

            existing_item.quantity = new_quantity
            existing_item.save()

            return existing_item

        return CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
        )

    def update(self, instance, validated_data):
        validated_data.pop("product", None)
        return super().update(instance, validated_data)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(
        many=True,
        read_only=True,
    )
    subtotal = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "items",
            "item_count",
            "subtotal",
            "updated_at",
        )
        read_only_fields = fields

    def get_subtotal(self, cart):
        return cart.subtotal

    def get_item_count(self, cart):
        return sum(
            item.quantity
            for item in cart.items.all()
        )


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_sku",
            "unit_price",
            "unit_discount",
            "quantity",
            "line_total",
        )
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "status",
            "payment_status",
            "payment_method",
            "currency",
            "subtotal",
            "product_discount_amount",
            "coupon_discount_amount",
            "shipping_amount",
            "total_amount",
            "discount_code_text",
            "shipping_title",
            "shipping_province",
            "shipping_city",
            "shipping_address_line",
            "shipping_postal_code",
            "shipping_recipient_name",
            "shipping_recipient_phone",
            "notes",
            "items",
            "created_at",
        )
        read_only_fields = fields


class AdminOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("status",)

    allowed_transitions = {
        Order.Status.PENDING: {
            Order.Status.CONFIRMED,
            Order.Status.CANCELLED,
        },
        Order.Status.CONFIRMED: {Order.Status.PROCESSING},
        Order.Status.PROCESSING: {Order.Status.SHIPPED},
        Order.Status.SHIPPED: {Order.Status.DELIVERED},
    }

    def validate_status(self, value):
        current_status = self.instance.status

        if value == current_status:
            return value

        allowed = self.allowed_transitions.get(current_status, set())
        if value not in allowed:
            raise serializers.ValidationError(
                f"Cannot change order status from {current_status} to {value}."
            )

        if value == Order.Status.CANCELLED:
            if self.instance.payment_status != Order.PaymentStatus.UNPAID:
                raise serializers.ValidationError(
                    "Paid orders cannot be cancelled."
                )

        return value

    def update(self, instance, validated_data):
        new_status = validated_data["status"]
        instance.status = new_status

        if new_status == Order.Status.CANCELLED:
            instance.cancelled_at = timezone.now()
            update_fields = ["status", "cancelled_at", "updated_at"]
        else:
            update_fields = ["status", "updated_at"]

        instance.save(update_fields=update_fields)
        return instance


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.PrimaryKeyRelatedField(
        source="address",
        queryset=Address.objects.all(),
    )
    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices,
        default=Order.PaymentMethod.MOCK,
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
    )

    def validate_address(self, address):
        if address.customer_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "The selected address does not belong to you."
            )
        return address

    @transaction.atomic
    def create(self, validated_data):
        cart = Cart.objects.select_for_update().get(
            pk=self.context["cart"].pk,
        )
        items = list(
            CartItem.objects.select_for_update()
            .filter(cart=cart)
            .select_related("product")
        )

        if not items:
            raise serializers.ValidationError(
                {"cart": "Cannot create an order from an empty cart."}
            )

        address = validated_data["address"]
        subtotal = Decimal("0.00")
        product_discount_amount = Decimal("0.00")
        snapshots = []

        for item in items:
            product = Product.objects.select_for_update().get(
                pk=item.product_id,
            )

            if not product.is_active:
                raise serializers.ValidationError(
                    {"cart": "The cart contains an inactive product."}
                )

            if item.quantity > product.stock_quantity:
                raise serializers.ValidationError(
                    {"cart": "The cart contains more items than available stock."}
                )

            unit_discount = Decimal("0.00")
            product_discount = getattr(product, "discount", None)
            if product_discount is not None:
                unit_discount = product_discount.calculate_discount(product.price)

            subtotal += product.price * item.quantity
            product_discount_amount += unit_discount * item.quantity
            snapshots.append((product, item, unit_discount))

        subtotal = subtotal.quantize(Decimal("0.01"))
        product_discount_amount = product_discount_amount.quantize(Decimal("0.01"))
        coupon_discount_amount = Decimal("0.00")
        discount_code = None
        coupon_code = validated_data.get("coupon_code", "").strip().upper()

        if coupon_code:
            try:
                discount_code = DiscountCode.objects.select_for_update().get(
                    code=coupon_code,
                )
            except DiscountCode.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"coupon_code": "Invalid discount code."}
                ) from exc

            if not discount_code.is_valid_now:
                raise serializers.ValidationError(
                    {"coupon_code": "This discount code is no longer valid."}
                )

            if subtotal < discount_code.minimum_order_amount:
                raise serializers.ValidationError(
                    {
                        "coupon_code": (
                            "The order does not meet the minimum amount "
                            "for this discount code."
                        )
                    }
                )

            coupon_discount_amount = discount_code.calculate_discount(subtotal)

        total_amount = (
            subtotal - product_discount_amount - coupon_discount_amount
        ).quantize(Decimal("0.01"))

        order = Order.objects.create(
            customer=self.context["request"].user,
            payment_method=validated_data.get(
                "payment_method",
                Order.PaymentMethod.MOCK,
            ),
            subtotal=subtotal,
            product_discount_amount=product_discount_amount,
            coupon_discount_amount=coupon_discount_amount,
            total_amount=total_amount,
            discount_code=discount_code,
            discount_code_text=discount_code.code if discount_code else "",
            shipping_title=address.title,
            shipping_province=address.province,
            shipping_city=address.city,
            shipping_address_line=address.address_line,
            shipping_postal_code=address.postal_code,
            shipping_recipient_name=address.recipient_name,
            shipping_recipient_phone=address.recipient_phone,
            notes=validated_data.get("notes", ""),
        )

        for product, item, unit_discount in snapshots:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_sku=product.sku,
                unit_price=product.price,
                unit_discount=unit_discount,
                quantity=item.quantity,
            )
            product.stock_quantity -= item.quantity
            product.save(update_fields=["stock_quantity", "updated_at"])

        if discount_code is not None:
            discount_code.used_count += 1
            discount_code.save(update_fields=["used_count", "updated_at"])

        CartItem.objects.filter(cart=cart).delete()
        return order
