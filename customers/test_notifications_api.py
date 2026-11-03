from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Discount

from .models import Customer, CustomerNotification
from .tasks import issue_birthday_discount_notifications


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="notify-user",
            email="notify@example.com",
            password="SecurePass#2026",
        )
        self.other = Customer.objects.create_user(
            username="notify-other",
            email="other-notify@example.com",
            password="SecurePass#2026",
        )
        self.url = reverse("customer-notification-list")

    def test_notifications_are_private_and_can_be_marked_read(self):
        CustomerNotification.objects.create(
            customer=self.customer,
            kind="campaign",
            title="Campaign",
            body="A new offer is live.",
            link="/#catalog",
        )
        CustomerNotification.objects.create(
            customer=self.other,
            kind="campaign",
            title="Private",
            body="Not yours.",
        )
        self.client.force_authenticate(self.customer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        notification_id = response.data["results"][0]["id"]
        read_response = self.client.post(
            reverse("customer-notification-mark-read", kwargs={"pk": notification_id}),
            {},
            format="json",
        )

        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertTrue(read_response.data["is_read"])


class BirthdayDiscountTaskTests(TestCase):
    @patch("customers.tasks.jalali_date_parts", return_value=(1405, 1, 1))
    def test_birthday_code_is_personal_and_emailed_once(self, mocked_date):
        customer = Customer.objects.create_user(
            username="birthday-user",
            email="birthday@example.com",
            password="SecurePass#2026",
            date_of_birth="1400/01/01",
        )

        self.assertEqual(issue_birthday_discount_notifications(), 1)
        self.assertEqual(issue_birthday_discount_notifications(), 0)
        code = customer.personal_discount_codes.get()
        self.assertEqual(code.customer_id, customer.id)
        self.assertEqual(code.discount_type, Discount.DiscountType.PERCENTAGE)
        self.assertEqual(CustomerNotification.objects.filter(customer=customer).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
