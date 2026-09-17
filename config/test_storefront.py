from pathlib import Path

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
        self.assertContains(response, 'class="cart-button icon-action-button"')
        self.assertContains(response, 'class="cart-label sr-only"')
        self.assertContains(response, 'data-cart-count')
        self.assertContains(response, "/static/storefront/js/cart-nav.js")
        self.assertContains(response, "/static/storefront/css/app.css")
        self.assertContains(response, "/static/storefront/js/favorites.js")
        self.assertContains(response, "/static/storefront/js/app.js")
        self.assertContains(response, 'id="compare-bar"')
        self.assertContains(response, 'id="compare-modal"')
        self.assertContains(response, 'id="catalog-count"')
        self.assertContains(response, 'id="recently-viewed"')
        self.assertContains(response, 'id="clear-recently-viewed"')
        self.assertContains(response, 'id="feedback-form"')
        self.assertNotContains(response, 'href="#feedback"')
        self.assertContains(response, "/static/storefront/js/feedback.js")
        self.assertContains(response, 'id="featured-grid"')
        self.assertContains(response, 'id="discounts"')
        self.assertContains(response, 'id="discount-grid"')
        self.assertContains(response, 'href="/discounts/"')
        self.assertContains(response, 'id="editor-pick"')
        self.assertContains(response, 'id="shipping-progress"')
        self.assertContains(response, 'data-catalog-filter="discount"')
        self.assertContains(response, 'data-catalog-filter="stock"')
        self.assertContains(response, 'id="price-filter"')
        self.assertContains(response, 'id="search-suggestions"')
        self.assertContains(response, 'aria-autocomplete="list"')
        self.assertContains(response, "/about/")
        self.assertContains(response, "/contact/")

    def test_catalog_search_has_localized_suggestions_and_keyboard_navigation(self):
        project_root = Path(__file__).resolve().parents[1]
        app_source = (project_root / "static/storefront/js/app.js").read_text()
        i18n_source = (project_root / "static/storefront/js/i18n.js").read_text()

        self.assertIn("function normalizeSearch", app_source)
        self.assertIn("function renderSearchSuggestions", app_source)
        self.assertIn("data-search-product", app_source)
        self.assertIn("ArrowDown", app_source)
        self.assertIn("searchNoResults", i18n_source)
        self.assertIn("const productDescriptions", i18n_source)

    def test_public_feedback_wall_loads_all_api_pages(self):
        source = (Path(__file__).resolve().parents[1] / "static/storefront/js/feedback.js").read_text()

        self.assertIn("data.next", source)
        self.assertIn("pageCount < 100", source)
        self.assertIn("feedbackItems = items", source)

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
        self.assertContains(response, "nexorastore.zp@gmail.com")
        self.assertContains(response, "openstreetmap.org/export/embed.html")
        self.assertContains(response, 'id="faq"')
        self.assertContains(response, 'class="faq-question"')
        self.assertContains(response, "/static/storefront/js/site.js")

    def test_discounts_page_is_available(self):
        response = self.client.get(reverse("storefront-discounts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "discounts-page")
        self.assertContains(response, 'id="discount-grid"')
        self.assertContains(response, 'id="discount-sort"')
        self.assertContains(response, 'id="discounts-best-saving"')
        self.assertContains(response, "/static/storefront/js/discounts.js")

    def test_storefront_pages_expose_shared_cart_navigation(self):
        pages = (
            ("storefront-about", {}),
            ("storefront-contact", {}),
            ("storefront-discounts", {}),
            ("storefront-product-detail", {"slug": "sample-product"}),
            ("storefront-checkout", {}),
            ("storefront-order-result", {}),
            ("storefront-account", {}),
            ("storefront-dashboard", {}),
            ("storefront-favorites", {}),
            ("storefront-profile", {}),
        )
        for name, kwargs in pages:
            with self.subTest(page=name):
                response = self.client.get(reverse(name, kwargs=kwargs))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="cart-button icon-action-button"')
                self.assertContains(response, 'data-cart-count')
                self.assertContains(response, "/static/storefront/js/cart-nav.js")

    def test_product_detail_page_is_available(self):
        response = self.client.get(reverse("storefront-product-detail", kwargs={"slug": "sample-product"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "product-detail")
        self.assertContains(response, 'id="product-recommendations"')
        self.assertContains(response, 'id="product-recommendations-grid"')
        self.assertContains(response, 'id="product-reviews"')
        self.assertContains(response, 'class="reviews-layout"')
        self.assertContains(response, 'id="reviews-list"')
        self.assertContains(response, 'id="review-sort"')
        self.assertContains(response, 'value="helpful"')
        self.assertContains(response, 'id="product-questions"')
        self.assertContains(response, 'id="questions-list"')
        self.assertContains(response, 'id="question-composer"')
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
        self.assertContains(response, 'class="dashboard-overview"')
        self.assertContains(response, 'id="dashboard-stat-orders"')
        self.assertContains(response, 'id="dashboard-stat-addresses"')
        self.assertContains(response, 'id="dashboard-stat-favorites"')
        self.assertContains(response, 'id="dashboard-stat-rewards"')
        self.assertContains(response, "/static/storefront/js/dashboard.js")

    def test_favorites_page_is_available(self):
        response = self.client.get(reverse("storefront-favorites"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "favorites-page")
        self.assertContains(response, "/static/storefront/js/favorites-page.js")
        self.assertContains(response, 'href="/favorites/"')

    def test_quick_cart_actions_are_available_in_secondary_product_shelves(self):
        project_root = Path(__file__).resolve().parents[1]
        product_detail_js = (project_root / "static/storefront/js/product-detail.js").read_text()
        favorites_js = (project_root / "static/storefront/js/favorites-page.js").read_text()

        self.assertIn("data-recommendation-cart", product_detail_js)
        self.assertIn("data-favorite-cart-icon", favorites_js)
        self.assertIn("NexoraCartNav?.refresh", favorites_js)

    def test_profile_page_is_available(self):
        response = self.client.get(reverse("storefront-profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ویرایش پروفایل")
        self.assertContains(response, 'href="/favorites/"')
        self.assertContains(response, 'data-panel="favorites"')
        self.assertContains(response, 'data-panel="watches"')
        self.assertContains(response, 'data-panel="rewards"')
        self.assertContains(response, 'data-panel="orders"')
        self.assertContains(response, 'data-profile-shortcut="orders"')
        self.assertContains(response, 'id="profile-orders"')
        self.assertContains(response, 'id="profile-orders-count"')
        self.assertContains(response, 'id="profile-watches-count"')
        self.assertContains(response, 'id="profile-reward-points"')
        self.assertContains(response, 'id="profile-completion-progress"')
        self.assertContains(response, 'data-profile-shortcut="addresses"')
        self.assertContains(response, 'data-profile-shortcut="favorites"')
        self.assertContains(response, 'id="profile-verified"')
        self.assertContains(response, 'class="profile-hero"')
        self.assertContains(response, 'class="favorite-nav-link"')
        self.assertContains(response, "/static/storefront/js/favorites.js")
        self.assertContains(response, "/static/storefront/js/profile.js")
        self.assertContains(response, "/static/storefront/js/password-toggle.js")

    @override_settings(DEBUG=False)
    def test_custom_error_pages_are_configured(self):
        response = self.client.get("/definitely-missing-page/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "این صفحه اینجا نیست.", status_code=404)
