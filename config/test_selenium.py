import os
import unittest
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from customers.models import Customer, Favorite, SiteFeedback
from products.models import Category, Discount, Product


@unittest.skipUnless(
    os.environ.get("RUN_SELENIUM") == "1",
    "Run with RUN_SELENIUM=1 to execute browser tests.",
)
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    # A browser smoke suite intentionally makes many requests in a few
    # seconds. Keep production throttling enabled while preventing the
    # shared test client IP from masking UI failures with HTTP 429 responses.
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": (),
    },
)
class StorefrontShoppingSeleniumTests(StaticLiveServerTestCase):
    """A real browser smoke test for the guest shopping journey."""

    @classmethod
    def setUpClass(cls):
        # DRF copies DEFAULT_THROTTLE_CLASSES onto APIView when the module is
        # imported, so override_settings alone does not affect the live
        # server's already-loaded view classes. Disable throttling only for
        # this browser smoke suite; production settings remain unchanged.
        cls._selenium_throttle_patch = patch.object(APIView, "throttle_classes", ())
        cls._selenium_throttle_patch.start()
        cls.addClassCleanup(cls._selenium_throttle_patch.stop)
        super().setUpClass()
        options = Options()
        options.binary_location = os.environ.get("CHROME_BINARY", "/usr/bin/google-chrome")
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1440,1000")
        driver_path = os.environ.get("CHROMEDRIVER_PATH")
        service = Service(driver_path) if driver_path else None
        cls.driver = webdriver.Chrome(service=service, options=options)
        cls.driver.implicitly_wait(1)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "driver", None) is not None:
            cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.driver.delete_all_cookies()
        self.category = Category.objects.create(name="Selenium audio", slug="selenium-audio")
        self.product = Product.objects.create(
            name="Selenium Headphones",
            slug="selenium-headphones",
            sku="SEL-001",
            category=self.category,
            brand="Nexora",
            price="1250000.00",
            stock_quantity=5,
        )

    def test_guest_can_compare_two_products(self):
        second_category = Category.objects.create(name="Selenium desk", slug="selenium-desk")
        second_product = Product.objects.create(
            name="Selenium Keyboard",
            slug="selenium-keyboard",
            sku="SEL-002",
            category=second_category,
            brand="Nexora",
            price="950000.00",
            stock_quantity=8,
        )
        self.driver.get(f"{self.live_server_url}/")
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.get(f"{self.live_server_url}/")

        compare_buttons = self.wait_for(
            lambda driver: driver.find_elements(By.CSS_SELECTOR, ".compare-button")
            if len(driver.find_elements(By.CSS_SELECTOR, ".compare-button")) >= 2
            else False,
        )
        for button in compare_buttons[:2]:
            product_id = button.get_attribute("data-compare-product")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", button)
            # Headless Chrome reports an incorrect off-screen click coordinate for this card action.
            self.driver.execute_script("arguments[0].click();", button)
            self.wait_for(
                lambda driver, product_id=product_id: driver.find_element(
                    By.CSS_SELECTOR,
                    f".compare-button[data-compare-product='{product_id}']",
                ).get_attribute("aria-pressed") == "true",
            )
        self.wait_for(EC.visibility_of_element_located((By.ID, "compare-bar")))
        compare_open = self.wait_for(EC.element_to_be_clickable((By.ID, "compare-open")))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", compare_open)
        ActionChains(self.driver).move_to_element(compare_open).click().perform()
        self.wait_for(EC.visibility_of_element_located((By.CSS_SELECTOR, ".compare-modal.open .compare-table")))
        comparison = self.driver.find_element(By.CSS_SELECTOR, ".compare-modal.open").text
        self.assertIn(self.product.name, comparison)
        self.assertIn(second_product.name, comparison)
        self.driver.find_element(By.ID, "compare-close").click()
        self.wait_for(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".compare-modal.open")))

    def test_dark_mode_keeps_the_page_canvas_dark(self):
        self.driver.get(f"{self.live_server_url}/")
        self.driver.execute_script("window.localStorage.removeItem('nexora-theme');")
        self.driver.refresh()

        theme_button = self.wait_for(
            EC.element_to_be_clickable((By.ID, "theme-toggle")),
        )
        self.driver.execute_script("arguments[0].click();", theme_button)

        self.wait_for(
            lambda driver: "dark" in driver.find_element(
                By.TAG_NAME,
                "html",
            ).get_attribute("class"),
        )
        artwork = self.driver.execute_script(
            """
            const canvas = document.querySelector('main.storefront-home');
            const pseudo = getComputedStyle(canvas, '::before');
            return { opacity: pseudo.opacity, blend: pseudo.mixBlendMode };
            """
        )

        self.assertEqual(artwork["opacity"], "0.22")
        self.assertEqual(artwork["blend"], "soft-light")

    def test_english_mode_renders_ltr_shell_and_hero_carousel(self):
        self.driver.get(f"{self.live_server_url}/")
        self.driver.execute_script("window.localStorage.setItem('nexora-language', 'en');")
        self.driver.refresh()

        self.wait_for(
            lambda driver: driver.find_element(By.TAG_NAME, "html").get_attribute("lang") == "en",
        )
        self.wait_for(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#hero-carousel:not([hidden]) .hero-carousel-product")),
        )

        html = self.driver.find_element(By.TAG_NAME, "html")
        self.assertEqual(html.get_attribute("dir"), "ltr")
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "[data-contact-phone]").text,
            "+98 21 4365 8791",
        )
        self.assertGreaterEqual(
            len(self.driver.find_elements(By.CSS_SELECTOR, "#hero-carousel-dots .hero-carousel-dot")),
            1,
        )
        self.assertTrue(
            self.driver.find_element(By.CSS_SELECTOR, "#hero-carousel .hero-carousel-image img").get_attribute("src"),
        )

    def test_discounted_product_appears_in_discount_shelf_and_offer_carousel(self):
        Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value="15.00",
            starts_at=timezone.now() - timedelta(minutes=1),
            ends_at=timezone.now() + timedelta(days=2),
            is_active=True,
        )
        self.driver.get(f"{self.live_server_url}/")

        self.wait_for(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#discounts:not([hidden]) #discount-grid .product-card")),
        )
        self.wait_for(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#offer-spotlight:not([hidden]) #offer-spotlight-product")),
        )
        self.assertTrue(
            self.driver.find_element(By.CSS_SELECTOR, "#discount-grid .discount-badge").is_displayed(),
        )
        self.assertTrue(
            self.driver.find_element(By.CSS_SELECTOR, "#discount-grid .price-stack del").is_displayed(),
        )

    def wait_for(self, condition):
        return WebDriverWait(self.driver, 10).until(condition)

    def test_guest_can_add_product_update_cart_and_reach_checkout(self):
        self.driver.get(f"{self.live_server_url}/")
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.get(f"{self.live_server_url}/")

        add_button = self.wait_for(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".add-button:not([disabled])")),
        )
        ActionChains(self.driver).move_to_element(add_button).click().perform()

        cart_toggle = self.wait_for(
            EC.element_to_be_clickable((By.ID, "cart-toggle")),
        )
        cart_toggle.click()
        self.wait_for(EC.visibility_of_element_located((By.CSS_SELECTOR, ".cart-drawer.open .cart-item")))

        self.wait_for(
            lambda driver: driver.execute_script(
                """
                const button = document.querySelector(".cart-drawer.open [data-action='increase']");
                if (!button || button.disabled) return false;
                button.click();
                return true;
                """,
            ),
        )
        self.wait_for(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, ".cart-drawer.open .quantity-control span"),
                "۲",
            ),
        )

        self.wait_for(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".toast-message")),
        )
        self.wait_for(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".drawer-checkout")),
        ).click()
        self.wait_for(EC.url_contains("/checkout/"))
        self.wait_for(EC.visibility_of_element_located((By.ID, "checkout-alert")))
        self.assertTrue(
            self.driver.find_element(
                By.CSS_SELECTOR,
                "#checkout-alert a[href^='/account/']",
            ).is_displayed(),
        )

    def test_guest_sees_recently_viewed_product_on_return(self):
        self.driver.get(f"{self.live_server_url}/products/{self.product.slug}/")
        self.wait_for(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#product-detail-content h1")),
        )

        self.driver.get(f"{self.live_server_url}/")
        recent_section = self.wait_for(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#recently-viewed:not([hidden])")),
        )
        self.wait_for(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#recently-viewed-grid .product-card")),
        )

        self.assertIn(self.product.name, recent_section.text)
        self.assertTrue(
            self.driver.find_element(
                By.CSS_SELECTOR,
                f"#recently-viewed-grid a[href='/products/{self.product.slug}/']",
            ).is_displayed(),
        )

    def test_guest_sees_related_products_on_product_detail(self):
        related = Product.objects.create(
            name="Selenium Related Headphones",
            slug="selenium-related-headphones",
            sku="SEL-004",
            category=self.category,
            brand="Nexora",
            price="1750000.00",
            stock_quantity=4,
        )
        self.driver.get(f"{self.live_server_url}/products/{self.product.slug}/")
        self.wait_for(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "#product-recommendations:not([hidden])"),
            ),
        )
        self.wait_for(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "#product-recommendations-grid .product-title-link"),
                related.name,
            ),
        )
        self.assertIn(
            related.name,
            self.driver.find_element(By.ID, "product-recommendations-grid").text,
        )

    def test_guest_can_submit_site_feedback(self):
        self.driver.get(f"{self.live_server_url}/")
        self.driver.execute_script("window.localStorage.removeItem('nexora-feedback-submitted');")
        self.driver.refresh()

        rating = self.wait_for(
            EC.presence_of_element_located((By.ID, "feedback-5")),
        )
        self.driver.execute_script("arguments[0].click();", rating)
        self.driver.find_element(By.CSS_SELECTOR, "#feedback-form textarea").send_keys("A clear and pleasant shopping experience.")
        submit = self.driver.find_element(By.CSS_SELECTOR, "#feedback-form button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", submit)
        self.driver.execute_script("arguments[0].click();", submit)
        self.wait_for(
            EC.text_to_be_present_in_element(
                (By.ID, "feedback-message"),
                "بازخوردت ثبت شد",
            ),
        )

        feedback = SiteFeedback.objects.latest("created_at")
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.page, "/")

    def test_guest_can_filter_catalog_to_available_products(self):
        self.out_of_stock_product = Product.objects.create(
            name="Selenium Sold Out Cable",
            slug="selenium-sold-out-cable",
            sku="SEL-003",
            category=self.category,
            brand="Nexora",
            price="450000.00",
            stock_quantity=0,
        )
        self.driver.get(f"{self.live_server_url}/")
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.get(f"{self.live_server_url}/")

        stock_filter = self.wait_for(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-catalog-filter='stock']")),
        )
        self.driver.execute_script("arguments[0].click();", stock_filter)
        self.wait_for(
            lambda driver: driver.find_element(
                By.CSS_SELECTOR,
                "[data-catalog-filter='stock']",
            ).get_attribute("aria-pressed") == "true",
        )
        self.wait_for(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "#product-grid .product-title-link"),
                self.product.name,
            ),
        )
        catalog_text = self.driver.find_element(By.ID, "product-grid").text
        self.assertIn(self.product.name, catalog_text)
        self.assertNotIn(self.out_of_stock_product.name, catalog_text)

    def test_guest_can_open_contact_faq(self):
        self.driver.get(f"{self.live_server_url}/contact/")
        question = self.wait_for(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".faq-question")),
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
            question,
        )
        self.driver.execute_script("arguments[0].click();", question)
        self.wait_for(lambda driver: question.get_attribute("aria-expanded") == "true")
        self.assertTrue(
            self.driver.find_element(
                By.CSS_SELECTOR,
                ".faq-item.open .faq-answer",
            ).is_displayed(),
        )

    def test_authenticated_customer_sees_saved_product_from_nav(self):
        customer = Customer.objects.create_user(
            username="selenium-favorite-user",
            email="selenium-favorite@example.com",
            password="SecurePass#2026",
        )
        Favorite.objects.create(customer=customer, product=self.product)
        refresh = RefreshToken.for_user(customer)

        self.driver.get(f"{self.live_server_url}/")
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.add_cookie(
            {
                "name": settings.AUTH_COOKIE_ACCESS,
                "value": str(refresh.access_token),
                "path": "/",
            },
        )
        self.driver.get(f"{self.live_server_url}/")

        favorite_nav = self.wait_for(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".favorite-nav-link")),
        )
        self.assertTrue(
            favorite_nav.get_attribute("href").endswith(
                "/favorites/",
            ),
        )
        self.wait_for(
            lambda driver: driver.find_element(
                By.CSS_SELECTOR,
                f".product-card [data-favorite-product='{self.product.pk}']",
            ).get_attribute("aria-pressed") == "true",
        )

        favorite_nav.click()
        self.wait_for(EC.url_contains("/favorites/"))
        self.wait_for(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".favorite-card")),
        )
        self.assertIn(
            self.product.name,
            self.driver.find_element(
                By.CSS_SELECTOR,
                "#favorites-list",
            ).text,
        )
