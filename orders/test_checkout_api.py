from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Address, Customer
from products.models import Category, Discount, DiscountCode, Product

from .models import Cart, CartItem, Order


class CheckoutAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="checkoutuser",
            email="checkout@example.com",
            password="SecurePass#2026",
        )
        category = Category.objects.create(name="Accessories")
        self.product = Product.objects.create(
            name="Nexora Headphones",
            sku="NEXORA-HEADPHONES-001",
            category=category,
            price=Decimal("250.00"),
            stock_quantity=4,
        )
        self.address = Address.objects.create(
            customer=self.customer,
            title="Home",
            province="Tehran",
            city="Tehran",
            address_line="Valiasr Street",
            postal_code="1234567890",
            recipient_name="Checkout User",
            recipient_phone="09120000000",
            is_default=True,
        )
        self.client.force_authenticate(self.customer)
        self.checkout_url = reverse("checkout")

    def add_to_cart(self, quantity=2):
        cart = Cart.objects.create(customer=self.customer)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=quantity,
        )
        return cart

    def test_checkout_creates_pending_order_without_consuming_stock(self):
        self.add_to_cart()

        response = self.client.post(
            self.checkout_url,
            {"address_id": self.address.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.subtotal, Decimal("500.00"))
        self.assertEqual(order.shipping_amount, Decimal("120000.00"))
        self.assertEqual(order.total_amount, Decimal("120500.00"))
        self.assertEqual(order.delivery_date, timezone.localdate() + timedelta(days=2))
        self.assertEqual(order.delivery_time_slot, Order.DeliveryTimeSlot.MORNING)
        self.assertEqual(order.items.get().product_name, self.product.name)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 4)
        self.assertTrue(CartItem.objects.exists())

    def test_checkout_persists_custom_delivery_schedule(self):
        self.add_to_cart()
        delivery_date = timezone.localdate() + timedelta(days=4)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "delivery_date": delivery_date.isoformat(),
                "delivery_time_slot": Order.DeliveryTimeSlot.EVENING,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.delivery_date, delivery_date)
        self.assertEqual(order.delivery_time_slot, Order.DeliveryTimeSlot.EVENING)
        self.assertEqual(response.data["delivery_date"], delivery_date.isoformat())
        self.assertEqual(response.data["delivery_time_slot"], Order.DeliveryTimeSlot.EVENING)

    def test_checkout_accepts_seven_day_delivery_boundary(self):
        self.add_to_cart()
        delivery_date = timezone.localdate() + timedelta(days=7)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "delivery_date": delivery_date.isoformat(),
                "delivery_time_slot": Order.DeliveryTimeSlot.MORNING,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_checkout_rejects_delivery_date_before_two_day_boundary(self):
        self.add_to_cart()
        delivery_date = timezone.localdate() + timedelta(days=1)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "delivery_date": delivery_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_date", response.data)
        self.assertFalse(Order.objects.exists())

    def test_checkout_rejects_delivery_date_after_seven_day_boundary(self):
        self.add_to_cart()
        delivery_date = timezone.localdate() + timedelta(days=8)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "delivery_date": delivery_date.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_date", response.data)
        self.assertFalse(Order.objects.exists())

    def test_checkout_rejects_unknown_delivery_time_slot(self):
        self.add_to_cart()
        delivery_date = timezone.localdate() + timedelta(days=2)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "delivery_date": delivery_date.isoformat(),
                "delivery_time_slot": "night",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_time_slot", response.data)
        self.assertFalse(Order.objects.exists())

    def test_checkout_uses_default_address_when_address_is_omitted(self):
        self.add_to_cart()

        response = self.client.post(
            self.checkout_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.shipping_title, self.address.title)
        self.assertEqual(order.shipping_address_line, self.address.address_line)

    def test_checkout_requires_an_address_when_no_default_exists(self):
        self.address.delete()
        self.add_to_cart()

        response = self.client.post(
            self.checkout_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("address_id", response.data)
        self.assertFalse(Order.objects.exists())

    def test_checkout_rejects_empty_cart(self):
        response = self.client.post(
            self.checkout_url,
            {"address_id": self.address.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cart", response.data)

    def test_checkout_rejects_insufficient_stock(self):
        self.add_to_cart(quantity=5)

        response = self.client.post(
            self.checkout_url,
            {"address_id": self.address.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_checkout_applies_coupon_without_consuming_usage(self):
        discount_code = DiscountCode.objects.create(
            code="NEXORA10",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
            usage_limit=2,
        )
        self.add_to_cart(quantity=2)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "coupon_code": "nexora10",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.coupon_discount_amount, Decimal("50.00"))
        self.assertEqual(order.shipping_amount, Decimal("120000.00"))
        self.assertEqual(order.total_amount, Decimal("120450.00"))
        self.assertEqual(order.discount_code_text, "NEXORA10")
        discount_code.refresh_from_db()
        self.assertEqual(discount_code.used_count, 0)

    def test_checkout_rejects_coupon_below_minimum_amount(self):
        DiscountCode.objects.create(
            code="MIN1000",
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("100.00"),
            minimum_order_amount=Decimal("1000.00"),
        )
        self.add_to_cart(quantity=1)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "coupon_code": "MIN1000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_checkout_rejects_a_personal_coupon_belonging_to_another_customer(self):
        other_customer = Customer.objects.create_user(
            username="other-coupon-owner",
            email="other-coupon-owner@example.com",
            password="Strong-password-123",
        )
        DiscountCode.objects.create(
            code="PRIVATE15",
            customer=other_customer,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("15.00"),
        )
        self.add_to_cart(quantity=1)

        response = self.client.post(
            self.checkout_url,
            {
                "address_id": self.address.pk,
                "coupon_code": "private15",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("coupon_code", response.data)
        self.assertIn("another customer", str(response.data["coupon_code"]))
        self.assertFalse(Order.objects.exists())

    def test_successful_mock_payment_consumes_stock_and_coupon(self):
        discount_code = DiscountCode.objects.create(
            code="PAY10",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
            usage_limit=1,
        )
        cart = self.add_to_cart()
        checkout_response = self.client.post(
            self.checkout_url,
            {"address_id": self.address.pk, "coupon_code": "PAY10"},
            format="json",
        )
        order = Order.objects.get()

        payment_response = self.client.post(
            reverse(
                "order-mock-payment",
                kwargs={"order_number": order.order_number},
            ),
            {"result": "success"},
            format="json",
        )

        self.assertEqual(checkout_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(payment_response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        discount_code.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        self.assertEqual(discount_code.used_count, 1)
        self.assertFalse(CartItem.objects.filter(cart=cart).exists())

    def test_failed_mock_payment_keeps_cart_and_stock_unchanged(self):
        cart = self.add_to_cart()
        checkout_response = self.client.post(
            self.checkout_url,
            {"address_id": self.address.pk},
            format="json",
        )
        order = Order.objects.get()

        payment_response = self.client.post(
            reverse(
                "order-mock-payment",
                kwargs={"order_number": order.order_number},
            ),
            {"result": "failed"},
            format="json",
        )

        self.assertEqual(checkout_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(payment_response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 4)
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        self.assertTrue(CartItem.objects.filter(cart=cart).exists())
