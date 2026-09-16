import os
import unittest

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from customers.models import Customer, Favorite
from products.models import Category, Product


@unittest.skipUnless(
    os.environ.get("RUN_SELENIUM") == "1",
    "Run with RUN_SELENIUM=1 to execute browser tests.",
)
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class StorefrontShoppingSeleniumTests(StaticLiveServerTestCase):
    """A real browser smoke test for the guest shopping journey."""

    @classmethod
    def setUpClass(cls):
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
        category = Category.objects.create(name="Selenium audio", slug="selenium-audio")
        self.product = Product.objects.create(
            name="Selenium Headphones",
            slug="selenium-headphones",
            sku="SEL-001",
            category=category,
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

        increase = self.driver.find_element(
            By.CSS_SELECTOR,
            ".cart-drawer.open [data-action='increase']",
        )
        increase.click()
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
