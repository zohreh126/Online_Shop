from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Customer
from .tasks import deactivate_unverified_customers


class CustomerTaskTests(TestCase):
    def test_deactivates_only_old_unverified_regular_customers(self):
        old_customer = Customer.objects.create_user(
            username="old-unverified",
            email="old-unverified@example.com",
            password="SecurePass#2026",
        )
        Customer.objects.filter(pk=old_customer.pk).update(
            date_joined=timezone.now() - timedelta(days=4),
        )
        recent_customer = Customer.objects.create_user(
            username="recent-unverified",
            email="recent-unverified@example.com",
            password="SecurePass#2026",
        )
        verified_customer = Customer.objects.create_user(
            username="old-verified",
            email="old-verified@example.com",
            password="SecurePass#2026",
        )
        Customer.objects.filter(pk=verified_customer.pk).update(
            date_joined=timezone.now() - timedelta(days=4),
            email_verified=True,
        )
        staff_customer = Customer.objects.create_user(
            username="old-staff",
            email="old-staff@example.com",
            password="SecurePass#2026",
            is_staff=True,
        )
        Customer.objects.filter(pk=staff_customer.pk).update(
            date_joined=timezone.now() - timedelta(days=4),
        )

        self.assertEqual(deactivate_unverified_customers(), 1)
        old_customer.refresh_from_db()
        recent_customer.refresh_from_db()
        verified_customer.refresh_from_db()
        staff_customer.refresh_from_db()
        self.assertFalse(old_customer.is_active)
        self.assertTrue(recent_customer.is_active)
        self.assertTrue(verified_customer.is_active)
        self.assertTrue(staff_customer.is_active)
