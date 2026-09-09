from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Customer

from .models import Order


class OrderActionAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="actionsuser",
            email="actions@example.com",
            password="SecurePass#2026",
        )
        self.client.force_authenticate(self.customer)

    def create_order(self, **kwargs):
        defaults = {
            "customer": self.customer,
            "subtotal": Decimal("100.00"),
            "total_amount": Decimal("100.00"),
            "shipping_title": "Home",
            "shipping_province": "Tehran",
            "shipping_city": "Tehran",
            "shipping_address_line": "Valiasr Street",
            "shipping_postal_code": "1234567890",
            "shipping_recipient_name": "Actions User",
            "shipping_recipient_phone": "09120000000",
        }
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def test_mock_payment_confirms_and_marks_order_paid(self):
        order = self.create_order()
        url = reverse(
            "order-pay",
            kwargs={"order_number": order.order_number},
        )

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertTrue(order.payment_reference.startswith("MOCK-"))
        self.assertIsNotNone(order.paid_at)

    def test_order_cannot_be_paid_twice(self):
        order = self.create_order()
        url = reverse(
            "order-pay",
            kwargs={"order_number": order.order_number},
        )
        self.client.post(url, {}, format="json")

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_unpaid_order_can_be_cancelled(self):
        order = self.create_order()
        url = reverse(
            "order-cancel",
            kwargs={"order_number": order.order_number},
        )

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertIsNotNone(order.cancelled_at)

    def test_paid_order_cannot_be_cancelled(self):
        order = self.create_order(
            status=Order.Status.CONFIRMED,
            payment_status=Order.PaymentStatus.PAID,
        )
        url = reverse(
            "order-cancel",
            kwargs={"order_number": order.order_number},
        )

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
