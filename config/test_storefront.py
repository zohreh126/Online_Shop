from django.test import TestCase
from django.urls import reverse


class StorefrontPageTests(TestCase):
    def test_storefront_home_is_available(self):
        response = self.client.get(reverse("storefront-home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NEXORA")
        self.assertContains(response, "product-grid")
        self.assertContains(response, "cart-drawer")
        self.assertContains(response, "/static/storefront/css/app.css")
        self.assertContains(response, "/static/storefront/js/app.js")

    def test_csrf_token_endpoint_is_available_to_storefront(self):
        response = self.client.get(reverse("auth-csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_checkout_page_is_available(self):
        response = self.client.get(reverse("storefront-checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تکمیل سفارش")
        self.assertContains(response, "/static/storefront/js/checkout.js")

    def test_account_page_is_available(self):
        response = self.client.get(reverse("storefront-account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ورود به حساب")
        self.assertContains(response, "/static/storefront/js/account.js")
