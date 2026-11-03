from decimal import Decimal

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from customers.models import Customer
from products.models import Category, Product

from .models import Cart, CartItem


class GuestCartAPITests(APITestCase):
    password = "SecurePass#2026"

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.customer = Customer.objects.create_user(
            username="guestmergeuser",
            email="guest-merge@example.com",
            password=self.password,
        )
        category = Category.objects.create(name="Guest Gadgets")
        self.product = Product.objects.create(
            name="Nexora Guest Keyboard",
            sku="NX-GUEST-KB-001",
            category=category,
            price=Decimal("100.00"),
            stock_quantity=5,
        )
        self.cart_url = reverse("cart-detail")
        self.items_url = reverse("cart-item-list")

    def test_guest_can_create_and_read_session_cart(self):
        response = self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cart_response = self.client.get(self.cart_url)
        self.assertEqual(cart_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_response.data["item_count"], 2)
        self.assertTrue(
            Cart.objects.filter(
                session_key=self.client.session.session_key,
                is_active=True,
            ).exists()
        )

    def test_guest_checkout_requires_authentication(self):
        response = self.client.post(
            reverse("checkout"),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_cart_merges_into_customer_cart_after_login(self):
        self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 2},
            format="json",
        )
        customer_cart = Cart.objects.create(customer=self.customer)
        CartItem.objects.create(
            cart=customer_cart,
            product=self.product,
            quantity=1,
        )
        guest_session_key = self.client.session.session_key

        csrf_response = self.client.get(reverse("auth-csrf"))
        csrf_token = csrf_response.cookies[settings.CSRF_COOKIE_NAME].value
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        login_response = self.client.post(
            reverse("auth-login"),
            {"username": self.customer.username, "password": self.password},
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        cart_response = self.client.get(self.cart_url)
        self.assertEqual(cart_response.data["item_count"], 3)
        self.assertEqual(cart_response.data["items"][0]["quantity"], 3)
        self.assertFalse(
            Cart.objects.filter(
                session_key=guest_session_key,
                is_active=True,
            ).exists()
        )
