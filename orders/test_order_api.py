from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Customer
from products.models import Category, Product

from .models import CartItem, Order, OrderItem


class OrderAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="ordersapiuser",
            email="orders-api@example.com",
            password="SecurePass#2026",
        )
        self.other_customer = Customer.objects.create_user(
            username="otherordersuser",
            email="other-orders@example.com",
            password="SecurePass#2026",
        )
        self.order = self.create_order(self.customer)
        self.other_order = self.create_order(self.other_customer)

    @staticmethod
    def create_order(customer):
        order = Order.objects.create(
            customer=customer,
            subtotal=Decimal("250.00"),
            total_amount=Decimal("250.00"),
            shipping_title="Home",
            shipping_province="Tehran",
            shipping_city="Tehran",
            shipping_address_line="Valiasr Street",
            shipping_postal_code="1234567890",
            shipping_recipient_name="Order User",
            shipping_recipient_phone="09120000000",
        )
        OrderItem.objects.create(
            order=order,
            product_name="Nexora Headphones",
            product_sku="NEXORA-HEADPHONES-001",
            unit_price=Decimal("250.00"),
            quantity=1,
        )
        return order

    def test_order_list_requires_authentication(self):
        response = self.client.get(reverse("order-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_sees_only_own_orders(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(reverse("order-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.order.pk,
        )

    def test_order_detail_contains_snapshot_items(self):
        self.client.force_authenticate(self.customer)
        url = reverse(
            "order-detail",
            kwargs={"order_number": self.order.order_number},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(
            response.data["items"][0]["product_name"],
            "Nexora Headphones",
        )

    def test_customer_cannot_access_another_customers_order(self):
        self.client.force_authenticate(self.customer)
        url = reverse(
            "order-detail",
            kwargs={"order_number": self.other_order.order_number},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_orders_api_is_read_only(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("order-list"),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_customer_can_reorder_own_order_into_active_cart(self):
        category = Category.objects.create(name="Reorder category")
        product = Product.objects.create(
            name="Reusable item",
            sku="REORDER-001",
            category=category,
            price=Decimal("100.00"),
            stock_quantity=5,
        )
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("200.00"),
            total_amount=Decimal("200.00"),
            shipping_title="Home",
            shipping_province="Tehran",
            shipping_city="Tehran",
            shipping_address_line="Valiasr Street",
            shipping_postal_code="1234567890",
            shipping_recipient_name="Order User",
            shipping_recipient_phone="09120000000",
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=product.price,
            quantity=2,
        )
        url = reverse(
            "order-reorder",
            kwargs={"order_number": order.order_number},
        )

        anonymous_response = self.client.post(url, format="json")
        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.client.force_authenticate(self.customer)
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["added"][0]["product_id"], product.pk)
        self.assertEqual(response.data["added"][0]["quantity"], 2)
        self.assertEqual(response.data["skipped"], [])
        self.assertEqual(response.data["cart"]["item_count"], 2)
        self.assertEqual(
            CartItem.objects.get(
                cart__customer=self.customer,
                product=product,
            ).quantity,
            2,
        )

        self.client.force_authenticate(self.other_customer)
        other_customer_response = self.client.post(url, format="json")
        self.assertEqual(
            other_customer_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_reorder_reports_partial_quantity_when_stock_is_limited(self):
        category = Category.objects.create(name="Limited stock category")
        product = Product.objects.create(
            name="Limited stock item",
            sku="REORDER-002",
            category=category,
            price=Decimal("75.00"),
            stock_quantity=1,
        )
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("225.00"),
            total_amount=Decimal("225.00"),
            shipping_title="Home",
            shipping_province="Tehran",
            shipping_city="Tehran",
            shipping_address_line="Valiasr Street",
            shipping_postal_code="1234567890",
            shipping_recipient_name="Order User",
            shipping_recipient_phone="09120000000",
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=product.price,
            quantity=3,
        )
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            reverse(
                "order-reorder",
                kwargs={"order_number": order.order_number},
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["added"][0]["quantity"], 1)
        self.assertEqual(len(response.data["skipped"]), 1)
        self.assertEqual(
            CartItem.objects.get(
                cart__customer=self.customer,
                product=product,
            ).quantity,
            1,
        )
