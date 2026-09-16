from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Category, Product

from .models import Customer, Favorite


class FavoriteAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="favorite-user",
            email="favorite-user@example.com",
            password="SecurePass#2026",
        )
        self.other_customer = Customer.objects.create_user(
            username="other-favorite-user",
            email="other-favorite-user@example.com",
            password="SecurePass#2026",
        )
        category = Category.objects.create(name="Favorite gadgets")
        self.product = Product.objects.create(
            name="Favorite Keyboard",
            slug="favorite-keyboard",
            sku="FAVORITE-KEYBOARD-001",
            category=category,
            brand="Nexora",
            price=Decimal("120.00"),
            stock_quantity=4,
        )
        self.inactive_product = Product.objects.create(
            name="Inactive Favorite",
            slug="inactive-favorite",
            sku="INACTIVE-FAVORITE-001",
            category=category,
            price=Decimal("80.00"),
            stock_quantity=1,
            is_active=False,
        )
        self.list_url = reverse("customer-favorite-list")
        self.toggle_url = reverse("customer-favorite-toggle")

    def authenticate(self, customer=None):
        self.client.force_authenticate(customer or self.customer)

    def test_favorites_require_authentication(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_add_and_list_favorite(self):
        self.authenticate()

        toggle_response = self.client.post(
            self.toggle_url,
            {"product_id": self.product.pk},
            format="json",
        )

        self.assertEqual(toggle_response.status_code, status.HTTP_200_OK)
        self.assertTrue(toggle_response.data["is_favorite"])
        self.assertEqual(
            toggle_response.data["favorite"]["product"]["id"],
            self.product.pk,
        )
        self.assertEqual(
            toggle_response.data["favorite"]["product"]["final_price"],
            Decimal("120.00"),
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["product"]["sku"], self.product.sku)

    def test_second_toggle_soft_deletes_and_third_toggle_restores(self):
        self.authenticate()

        self.client.post(
            self.toggle_url,
            {"product_id": self.product.pk},
            format="json",
        )
        remove_response = self.client.post(
            self.toggle_url,
            {"product_id": self.product.pk},
            format="json",
        )

        self.assertEqual(remove_response.status_code, status.HTTP_200_OK)
        self.assertFalse(remove_response.data["is_favorite"])
        favorite = Favorite.objects.get(
            customer=self.customer,
            product=self.product,
        )
        self.assertFalse(favorite.is_active)
        self.assertEqual(self.client.get(self.list_url).data["results"], [])

        restore_response = self.client.post(
            self.toggle_url,
            {"product_id": self.product.pk},
            format="json",
        )
        self.assertTrue(restore_response.data["is_favorite"])
        favorite.refresh_from_db()
        self.assertTrue(favorite.is_active)

    def test_delete_endpoint_is_logical_and_user_scoped(self):
        self.authenticate()
        self.client.post(
            self.toggle_url,
            {"product_id": self.product.pk},
            format="json",
        )
        favorite = Favorite.objects.get(
            customer=self.customer,
            product=self.product,
        )

        self.authenticate(self.other_customer)
        response = self.client.delete(
            reverse("customer-favorite-detail", kwargs={"pk": favorite.pk}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.authenticate()
        response = self.client.delete(
            reverse("customer-favorite-detail", kwargs={"pk": favorite.pk}),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        favorite.refresh_from_db()
        self.assertFalse(favorite.is_active)

    def test_favorites_are_isolated_between_customers(self):
        self.authenticate()
        self.client.post(
            self.toggle_url,
            {"product_id": self.product.pk},
            format="json",
        )

        self.authenticate(self.other_customer)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_inactive_products_cannot_be_bookmarked(self):
        self.authenticate()

        response = self.client.post(
            self.toggle_url,
            {"product_id": self.inactive_product.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
