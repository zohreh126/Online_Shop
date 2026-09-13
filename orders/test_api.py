from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Customer
from products.models import Category, Discount, DiscountCode, Product


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

    def test_cart_is_public_for_guest_users(self):
        response = self.client.get(self.cart_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])

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

    def test_cart_totals_use_current_product_discount(self):
        Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
        )
        self.authenticate()

        response = self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["unit_price"], "90.00")
        self.assertEqual(response.data["unit_discount"], "10.00")
        self.assertEqual(response.data["line_total"], "180.00")

        cart = self.client.get(self.cart_url)
        self.assertEqual(cart.data["subtotal"], Decimal("200.00"))
        self.assertEqual(cart.data["product_discount_amount"], Decimal("20.00"))
        self.assertEqual(cart.data["total_amount"], Decimal("180.00"))

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

    def test_coupon_can_be_applied_and_removed_from_cart(self):
        self.authenticate()
        self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 1},
            format="json",
        )
        DiscountCode.objects.create(
            code="CART10",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
        )

        apply_response = self.client.post(
            reverse("cart-coupon"),
            {"code": "cart10"},
            format="json",
        )
        self.assertEqual(apply_response.status_code, status.HTTP_200_OK)
        self.assertEqual(apply_response.data["coupon_code"], "CART10")

        remove_response = self.client.delete(reverse("cart-coupon"))
        self.assertEqual(
            remove_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertIsNone(self.client.get(self.cart_url).data["coupon_code"])

    def test_invalid_coupon_is_rejected(self):
        self.authenticate()
        self.client.post(
            self.items_url,
            {"product_id": self.product.pk, "quantity": 1},
            format="json",
        )

        response = self.client.post(
            reverse("cart-coupon"),
            {"code": "NOT-REAL"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
