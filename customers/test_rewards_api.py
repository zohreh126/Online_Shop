from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order, RewardTransaction

from .models import Customer


class RewardSummaryAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="reward-user",
            email="reward-user@example.com",
            password="SecurePass#2026",
        )
        self.other_customer = Customer.objects.create_user(
            username="other-reward-user",
            email="other-reward@example.com",
            password="SecurePass#2026",
        )
        self.url = reverse("customer-rewards")

    @staticmethod
    def create_order(customer, total):
        return Order.objects.create(
            customer=customer,
            subtotal=total,
            total_amount=total,
            shipping_title="Home",
            shipping_province="Tehran",
            shipping_city="Tehran",
            shipping_address_line="Valiasr Street",
            shipping_postal_code="1234567890",
            shipping_recipient_name="Reward User",
            shipping_recipient_phone="09120000000",
        )

    def test_rewards_require_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_summary_returns_balance_and_only_current_customer_transactions(self):
        first_order = self.create_order(self.customer, Decimal("300000.00"))
        second_order = self.create_order(self.customer, Decimal("100000.00"))
        other_order = self.create_order(self.other_customer, Decimal("900000.00"))
        RewardTransaction.objects.create(
            customer=self.customer,
            order=first_order,
            points=3,
            reason="First order reward",
        )
        RewardTransaction.objects.create(
            customer=self.customer,
            order=second_order,
            points=1,
            reason="Second order reward",
        )
        RewardTransaction.objects.create(
            customer=self.other_customer,
            order=other_order,
            points=9,
        )
        self.client.force_authenticate(self.customer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["balance"], 4)
        self.assertEqual(response.data["transaction_count"], 2)
        self.assertEqual(len(response.data["transactions"]), 2)
        self.assertEqual(response.data["transactions"][0]["order_number"], str(second_order.order_number))
