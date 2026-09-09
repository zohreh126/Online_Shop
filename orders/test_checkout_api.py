from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Address, Customer
from products.models import Category, Product

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

    def test_checkout_creates_order_snapshots_items_and_clears_cart(self):
        self.add_to_cart()

        response = self.client.post(
            self.checkout_url,
            {"address_id": self.address.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.subtotal, Decimal("500.00"))
        self.assertEqual(order.total_amount, Decimal("500.00"))
        self.assertEqual(order.items.get().product_name, self.product.name)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        self.assertFalse(CartItem.objects.exists())

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
