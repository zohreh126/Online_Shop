from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from customers.models import Customer
from products.models import Category, Product

from .models import Cart, CartItem, Order, OrderItem


class OrderTestBase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="orderuser",
            email="order@example.com",
            password="SecurePass#2026",
        )
        self.category = Category.objects.create(
            name="Electronics",
        )

    def create_product(self, sku="PRODUCT-001", **kwargs):
        defaults = {
            "name": f"Product {sku}",
            "sku": sku,
            "category": self.category,
            "price": Decimal("100.00"),
            "stock_quantity": 10,
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    def create_order(self, **kwargs):
        defaults = {
            "customer": self.customer,
            "shipping_title": "Home",
            "shipping_province": "Tehran",
            "shipping_city": "Tehran",
            "shipping_address_line": "Valiasr Street",
            "shipping_postal_code": "1234567890",
            "shipping_recipient_name": "Order User",
            "shipping_recipient_phone": "09120000000",
        }
        defaults.update(kwargs)
        return Order.objects.create(**defaults)


class CartModelTests(OrderTestBase):
    def test_cart_requires_customer_or_session(self):
        with self.assertRaises(ValidationError):
            Cart().full_clean()

    def test_cart_subtotal_is_calculated_from_items(self):
        product_one = self.create_product(
            sku="PRODUCT-001",
            price=Decimal("100.00"),
        )
        product_two = self.create_product(
            sku="PRODUCT-002",
            price=Decimal("25.50"),
        )
        cart = Cart.objects.create(customer=self.customer)

        CartItem.objects.create(
            cart=cart,
            product=product_one,
            quantity=2,
        )
        CartItem.objects.create(
            cart=cart,
            product=product_two,
            quantity=3,
        )

        self.assertEqual(
            cart.subtotal,
            Decimal("276.50"),
        )

    def test_cart_item_rejects_inactive_product(self):
        product = self.create_product(
            sku="INACTIVE-001",
            is_active=False,
        )
        cart = Cart.objects.create(customer=self.customer)

        with self.assertRaises(ValidationError):
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=1,
            )

    def test_cart_item_rejects_zero_quantity(self):
        product = self.create_product()
        cart = Cart.objects.create(customer=self.customer)

        with self.assertRaises(ValidationError):
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=0,
            )

    def test_cart_item_line_total_is_calculated(self):
        product = self.create_product(
            price=Decimal("75.25"),
        )
        cart = Cart.objects.create(customer=self.customer)

        item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=4,
        )

        self.assertEqual(
            item.line_total,
            Decimal("301.00"),
        )


class OrderModelTests(OrderTestBase):
    def test_order_number_is_generated(self):
        order = self.create_order()

        self.assertIsNotNone(order.order_number)
        self.assertEqual(
            order.status,
            Order.Status.PENDING,
        )
        self.assertEqual(
            order.payment_status,
            Order.PaymentStatus.UNPAID,
        )

    def test_order_item_keeps_product_snapshot(self):
        product = self.create_product(
            sku="SNAPSHOT-001",
            price=Decimal("250.00"),
        )
        order = self.create_order()

        item = OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=product.price,
            quantity=2,
        )

        self.assertEqual(
            item.product_name,
            product.name,
        )
        self.assertEqual(
            item.product_sku,
            product.sku,
        )
        self.assertEqual(
            item.line_total,
            Decimal("500.00"),
        )

    def test_order_item_applies_unit_discount(self):
        product = self.create_product(
            sku="DISCOUNTED-001",
            price=Decimal("100.00"),
        )
        order = self.create_order()

        item = OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=Decimal("100.00"),
            unit_discount=Decimal("15.00"),
            quantity=3,
        )

        self.assertEqual(
            item.line_total,
            Decimal("255.00"),
        )

    def test_order_item_rejects_discount_above_unit_price(self):
        product = self.create_product(
            sku="INVALID-DISCOUNT-001",
        )
        order = self.create_order()

        with self.assertRaises(ValidationError):
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_sku=product.sku,
                unit_price=Decimal("100.00"),
                unit_discount=Decimal("101.00"),
                quantity=1,
            )
