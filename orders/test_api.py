from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Customer
from products.models import Category, Product


class CartAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="cartuser",
            email="cart@example.com",
            password="SecurePass#2026",
        )
        self.other_customer = Customer.objects.create_user(
            username="othercartuser",
            email="othercart@example.com",
            password="SecurePass#2026",
        )
        self.category = Category.objects.create(name="Gadgets")
        self.product = Product.objects.create(
            name="Nexora Keyboard",
            sku="NEXORA-KEYBOARD-001",
            category=self.category,
            brand="Nexora",
            price=Decimal("100.00"),
            stock_quantity=5,
        )
        self.cart_url = reverse("cart-detail")
        self.items_url = reverse("cart-item-list")

    def authenticate(self, customer=None):
        self.client.force_authenticate(customer or self.customer)

    def test_cart_requires_authentication(self):
        response = self.client.get(self.cart_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_cart_creates_empty_active_cart(self):
        self.authenticate()

        response = self.client.get(self.cart_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["item_count"], 0)
        self.assertEqual(response.data["subtotal"], Decimal("0.00"))

    def test_add_item_and_duplicate_addition_increases_quantity(self):
        self.authenticate()

        first = self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 2},
            format="json",
        )
        second = self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 1},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.data["quantity"], 3)
        cart = self.client.get(self.cart_url)
        self.assertEqual(cart.data["item_count"], 3)
        self.assertEqual(cart.data["subtotal"], Decimal("300.00"))

    def test_item_quantity_cannot_exceed_stock(self):
        self.authenticate()

        response = self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 6},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)

    def test_customer_cannot_access_another_customers_item(self):
        self.authenticate()
        create_response = self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 1},
            format="json",
        )
        item_url = reverse(
            "cart-item-detail",
            kwargs={"pk": create_response.data["id"]},
        )

        self.authenticate(self.other_customer)
        response = self.client.get(item_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_item(self):
        self.authenticate()
        create_response = self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 1},
            format="json",
        )
        item_url = reverse(
            "cart-item-detail",
            kwargs={"pk": create_response.data["id"]},
        )

        response = self.client.delete(item_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(self.cart_url).data["items"], [])
