from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Address, Customer


class AddressAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="addressuser",
            email="address@example.com",
            password="SecurePass#2026",
        )
        self.other_customer = Customer.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="SecurePass#2026",
        )

        self.client.force_authenticate(user=self.customer)
        self.list_url = reverse("customer-address-list")

    @staticmethod
    def payload(**overrides):
        data = {
            "title": "Home",
            "province": "Tehran",
            "city": "Tehran",
            "address_line": "Valiasr Street",
            "postal_code": "1234567890",
            "recipient_name": "Test User",
            "recipient_phone": "09120000000",
        }
        data.update(overrides)
        return data

    def test_addresses_require_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_first_address_becomes_default_automatically(self):
        response = self.client.post(
            self.list_url,
            self.payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertNotIn("customer", response.data)

        address = Address.objects.get()
        self.assertEqual(address.customer, self.customer)
        self.assertTrue(address.is_default)

    def test_new_default_address_clears_previous_default(self):
        first_response = self.client.post(
            self.list_url,
            self.payload(title="Home"),
            format="json",
        )
        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.post(
            self.list_url,
            self.payload(
                title="Work",
                is_default=True,
            ),
            format="json",
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        addresses = Address.objects.filter(
            customer=self.customer,
        ).order_by("id")

        self.assertFalse(addresses[0].is_default)
        self.assertTrue(addresses[1].is_default)

    def test_user_can_only_list_own_addresses(self):
        own_address = Address.objects.create(
            customer=self.customer,
            **self.payload(),
        )
        other_address = Address.objects.create(
            customer=self.other_customer,
            **self.payload(title="Other"),
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            item["id"]
            for item in response.data["results"]
        }

        self.assertIn(own_address.id, returned_ids)
        self.assertNotIn(other_address.id, returned_ids)

    def test_user_cannot_access_another_users_address(self):
        other_address = Address.objects.create(
            customer=self.other_customer,
            **self.payload(title="Other"),
        )

        url = reverse(
            "customer-address-detail",
            kwargs={"pk": other_address.pk},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_can_update_and_delete_own_address(self):
        address = Address.objects.create(
            customer=self.customer,
            **self.payload(),
        )

        detail_url = reverse(
            "customer-address-detail",
            kwargs={"pk": address.pk},
        )

        update_response = self.client.patch(
            detail_url,
            {"city": "Shiraz"},
            format="json",
        )

        self.assertEqual(
            update_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            update_response.data["city"],
            "Shiraz",
        )

        delete_response = self.client.delete(detail_url)

        self.assertEqual(
            delete_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Address.objects.filter(pk=address.pk).exists()
        )

    def test_invalid_postal_code_is_rejected(self):
        response = self.client.post(
            self.list_url,
            self.payload(postal_code="12345"),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("postal_code", response.data)
