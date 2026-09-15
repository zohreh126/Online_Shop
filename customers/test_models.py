from django.test import TestCase

from .models import Customer


class CustomerModelTests(TestCase):
    def test_delete_deactivates_customer(self):
        customer = Customer.objects.create_user(
            username="archive-user",
            email="archive-user@example.com",
            password="SecurePass#2026",
        )

        customer.delete()
        customer.refresh_from_db()

        self.assertFalse(customer.is_active)
