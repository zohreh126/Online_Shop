from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Customer

from .models import Discount, DiscountCode


class ActiveCampaignAPITests(APITestCase):
    def test_active_public_campaign_excludes_personal_and_expired_codes(self):
        customer = Customer.objects.create_user(
            username="campaign-owner",
            email="campaign-owner@example.com",
            password="Strong-pass-2026",
        )
        DiscountCode.objects.create(
            code="PERSONAL15",
            customer=customer,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("15.00"),
        )
        DiscountCode.objects.create(
            code="EXPIRED10",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
            ends_at=timezone.now() - timedelta(minutes=1),
        )
        DiscountCode.objects.create(
            code="SPRING20",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("20.00"),
            minimum_order_amount=Decimal("2000000.00"),
            ends_at=timezone.now() + timedelta(days=5),
        )

        response = self.client.get(reverse("active-campaign"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["campaign"]["code"], "SPRING20")
        self.assertEqual(response.data["campaign"]["minimum_order_amount"], Decimal("2000000.00"))

    def test_campaign_endpoint_returns_null_when_no_global_code_is_valid(self):
        DiscountCode.objects.create(
            code="OLD10",
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("100.00"),
            is_active=False,
        )

        response = self.client.get(reverse("active-campaign"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["campaign"])

    def test_campaign_endpoint_skips_an_expired_latest_code(self):
        DiscountCode.objects.create(
            code="OLDERACTIVE",
            discount_type="percentage",
            value=10,
        )
        DiscountCode.objects.create(
            code="LATESTEXPIRED",
            discount_type="percentage",
            value=20,
            ends_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.get(reverse("active-campaign"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["campaign"]["code"], "OLDERACTIVE")
