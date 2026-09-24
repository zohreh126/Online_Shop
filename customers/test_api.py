from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Customer


class CustomerAuthAPITests(APITestCase):
    def test_registration_creates_customer_safely(self):
        payload = {
            "username": "newcustomer",
            "email": "newcustomer@example.com",
            "first_name": "New",
            "last_name": "Customer",
            "phone_number": "09120000000",
            "password": "SecurePass#2026",
            "password_confirm": "SecurePass#2026",
        }

        response = self.client.post(
            reverse("customer-register"),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_confirm", response.data)

        customer = Customer.objects.get(username="newcustomer")

        self.assertTrue(
            customer.check_password("SecurePass#2026")
        )
        self.assertFalse(customer.is_staff)
        self.assertTrue(customer.is_active)

    def test_registration_rejects_password_mismatch(self):
        payload = {
            "username": "anothercustomer",
            "email": "another@example.com",
            "password": "SecurePass#2026",
            "password_confirm": "DifferentPass#2026",
        }

        response = self.client.post(
            reverse("customer-register"),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("password_confirm", response.data)

    def test_registration_rejects_duplicate_username(self):
        Customer.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="SecurePass#2026",
        )

        payload = {
            "username": "existing",
            "email": "new@example.com",
            "password": "SecurePass#2026",
            "password_confirm": "SecurePass#2026",
        }

        response = self.client.post(
            reverse("customer-register"),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("username", response.data)

    def test_registration_allows_email_reuse_after_soft_delete(self):
        archived = Customer.objects.create_user(
            username="archived-customer",
            email="reusable@example.com",
            password="SecurePass#2026",
        )
        archived.delete()

        response = self.client.post(
            reverse("customer-register"),
            {
                "username": "new-customer",
                "email": "reusable@example.com",
                "password": "SecurePass#2026",
                "password_confirm": "SecurePass#2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Customer.objects.filter(email="reusable@example.com", is_active=True).count(),
            1,
        )

    def test_profile_requires_authentication(self):
        response = self.client.get(
            reverse("customer-profile")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_customer_can_view_profile(self):
        customer = Customer.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="SecurePass#2026",
            first_name="Profile",
            last_name="User",
        )

        self.client.force_authenticate(user=customer)

        response = self.client.get(
            reverse("customer-profile")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["username"],
            "profileuser",
        )
        self.assertEqual(
            response.data["email"],
            "profile@example.com",
        )
        self.assertNotIn("password", response.data)

    def test_authenticated_customer_can_update_profile(self):
        customer = Customer.objects.create_user(
            username="editableuser",
            email="editable@example.com",
            password="SecurePass#2026",
        )
        self.client.force_authenticate(user=customer)

        response = self.client.patch(
            reverse("customer-profile"),
            {"first_name": "زهره", "phone_number": "۰۹۱۲۳۴۵۶۷۸۹"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        customer.refresh_from_db()
        self.assertEqual(customer.first_name, "زهره")
