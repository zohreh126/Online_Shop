import os
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
        category = Category.objects.create(name="Selenium audio", slug="selenium-audio")
        Product.objects.create(
            name="Selenium Headphones",
            slug="selenium-headphones",
            sku="SEL-001",
            category=category,
            brand="Nexora",
            price="1250000.00",
            stock_quantity=5,
        )

    def wait_for(self, condition):
        return WebDriverWait(self.driver, 10).until(condition)

    def test_guest_can_add_product_update_cart_and_reach_checkout(self):
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
