from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class APIDocumentationTests(APITestCase):
    def test_openapi_schema_is_available(self):
        response = self.client.get(reverse("schema"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("paths", response.data)
        self.assertIn("/api/v1/products/", response.data["paths"])
        self.assertIn("/api/v1/products/{slug}/reviews/", response.data["paths"])
        self.assertIn("/api/v1/orders/", response.data["paths"])
        self.assertIn(
            "/api/v1/orders/{order_number}/mock-payment/",
            response.data["paths"],
        )
        self.assertIn("/api/v1/cart/checkout/", response.data["paths"])
        self.assertIn("/api/v1/auth/favorites/", response.data["paths"])
        self.assertIn("/api/v1/auth/favorites/toggle/", response.data["paths"])

    def test_swagger_ui_is_available(self):
        response = self.client.get(reverse("swagger-ui"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Nexora Store API")

    def test_redoc_is_available(self):
        response = self.client.get(reverse("redoc"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Nexora Store API")
