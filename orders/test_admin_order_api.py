from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Customer

from .models import Order


class AdminOrderAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="adminorderscustomer",
            email="admin-orders-customer@example.com",
            password="SecurePass#2026",
        )
        self.staff = Customer.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="SecurePass#2026",
            is_staff=True,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            shipping_title="Home",
            shipping_province="Tehran",
            shipping_city="Tehran",
            shipping_address_line="Valiasr Street",
            shipping_postal_code="1234567890",
            shipping_recipient_name="Admin Customer",
            shipping_recipient_phone="09120000000",
        )

    def admin_authenticate(self):
        self.client.force_authenticate(self.staff)

    def test_non_staff_cannot_access_admin_orders(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(reverse("admin-order-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_list_all_orders(self):
        self.admin_authenticate()

        response = self.client.get(reverse("admin-order-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_staff_can_advance_order_status(self):
        self.admin_authenticate()
        url = reverse("admin-order-detail", kwargs={"pk": self.order.pk})

        response = self.client.patch(
            url,
            {"status": Order.Status.CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    def test_invalid_status_transition_is_rejected(self):
        self.admin_authenticate()
        url = reverse("admin-order-detail", kwargs={"pk": self.order.pk})

        response = self.client.patch(
            url,
            {"status": Order.Status.SHIPPED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_staff_cannot_delete_orders(self):
        self.admin_authenticate()
        url = reverse("admin-order-detail", kwargs={"pk": self.order.pk})

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
