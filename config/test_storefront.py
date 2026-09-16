from django.test import TestCase, override_settings
from django.urls import reverse


class StorefrontPageTests(TestCase):
    def test_storefront_home_is_available(self):
        response = self.client.get(reverse("storefront-home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NEXORA")
        self.assertContains(response, "product-grid")
        self.assertContains(response, "cart-drawer")
        self.assertContains(response, 'class="favorite-nav-link"')
        self.assertContains(response, 'data-favorite-count')
        self.assertContains(response, "/static/storefront/css/app.css")
        self.assertContains(response, "/static/storefront/js/favorites.js")
        self.assertContains(response, "/static/storefront/js/app.js")
        self.assertContains(response, "/about/")
        self.assertContains(response, "/contact/")

    def test_about_page_is_available(self):
        response = self.client.get(reverse("storefront-about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "about-page")
        self.assertContains(response, "داستان ما")
        self.assertContains(response, "/static/storefront/js/site.js")

    def test_contact_page_contains_contact_details_and_map(self):
        response = self.client.get(reverse("storefront-contact"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "contact-page")
        self.assertContains(response, "support@nexora.example")
        self.assertContains(response, "openstreetmap.org/export/embed.html")
        self.assertContains(response, "/static/storefront/js/site.js")

    def test_product_detail_page_is_available(self):
        response = self.client.get(reverse("storefront-product-detail", kwargs={"slug": "sample-product"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "product-detail")
        self.assertContains(response, "/static/storefront/js/favorites.js")
        self.assertContains(response, "/static/storefront/js/product-detail.js")

    def test_csrf_token_endpoint_is_available_to_storefront(self):
        response = self.client.get(reverse("auth-csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_checkout_page_is_available(self):
        response = self.client.get(reverse("storefront-checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تکمیل سفارش")
        self.assertContains(response, "/static/storefront/js/checkout.js")

    def test_order_result_page_is_available(self):
        response = self.client.get(reverse("storefront-order-result"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "order-result")
        self.assertContains(response, "/static/storefront/js/order-result.js")

    def test_account_page_is_available(self):
        response = self.client.get(reverse("storefront-account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ورود به حساب")
        self.assertContains(response, "/static/storefront/js/account.js")
        self.assertContains(response, "/static/storefront/js/password-toggle.js")
        self.assertContains(response, 'data-password-toggle="register-password"')

    def test_dashboard_page_is_available(self):
        response = self.client.get(reverse("storefront-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "داشبورد مشتری")
        self.assertContains(response, 'href="/favorites/"')
        self.assertContains(response, "/static/storefront/js/dashboard.js")

    def test_favorites_page_is_available(self):
        response = self.client.get(reverse("storefront-favorites"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "favorites-page")
        self.assertContains(response, "/static/storefront/js/favorites-page.js")
        self.assertContains(response, 'href="/favorites/"')

    def test_profile_page_is_available(self):
        response = self.client.get(reverse("storefront-profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ویرایش پروفایل")
        self.assertContains(response, 'href="/favorites/"')
        self.assertContains(response, 'data-panel="favorites"')
        self.assertContains(response, 'class="favorite-nav-link"')
        self.assertContains(response, "/static/storefront/js/favorites.js")
        self.assertContains(response, "/static/storefront/js/profile.js")
        self.assertContains(response, "/static/storefront/js/password-toggle.js")

    @override_settings(DEBUG=False)
    def test_custom_error_pages_are_configured(self):
        response = self.client.get("/definitely-missing-page/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "این صفحه اینجا نیست.", status_code=404)
