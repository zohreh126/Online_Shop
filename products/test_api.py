from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Discount, Product


class ProductCatalogAPITests(APITestCase):
    def setUp(self):
        self.electronics = Category.objects.create(
            name="Electronics",
        )
        self.audio = Category.objects.create(
            name="Audio",
            parent=self.electronics,
        )
        Category.objects.create(
            name="Hidden",
            is_active=False,
        )

        self.keyboard = self.create_product(
            name="Mechanical Keyboard",
            sku="KEYBOARD-001",
            category=self.electronics,
            price=Decimal("100.00"),
            stock_quantity=10,
            brand="Nexora",
            specifications={"layout": "US", "connection": "USB-C"},
        )
        self.headphones = self.create_product(
            name="Wireless Headphones",
            sku="HEADPHONES-001",
            category=self.audio,
            price=Decimal("250.00"),
            stock_quantity=5,
            brand="SoundPeak",
        )
        self.out_of_stock = self.create_product(
            name="USB Cable",
            sku="CABLE-001",
            category=self.electronics,
            price=Decimal("20.00"),
            stock_quantity=0,
        )
        self.inactive_product = self.create_product(
            name="Inactive Product",
            sku="INACTIVE-001",
            category=self.electronics,
            price=Decimal("500.00"),
            stock_quantity=10,
            is_active=False,
        )

    @staticmethod
    def create_product(**kwargs):
        return Product.objects.create(**kwargs)

    def test_product_list_is_public_and_excludes_inactive_products(self):
        response = self.client.get(reverse("product-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

        slugs = {
            item["slug"]
            for item in response.data["results"]
        }

        self.assertIn(self.keyboard.slug, slugs)
        self.assertIn(self.headphones.slug, slugs)
        self.assertIn(self.out_of_stock.slug, slugs)
        self.assertNotIn(self.inactive_product.slug, slugs)

    def test_product_detail_works_with_slug(self):
        url = reverse(
            "product-detail",
            kwargs={"slug": self.keyboard.slug},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["sku"], "KEYBOARD-001")
        self.assertEqual(
            response.data["category"]["slug"],
            self.electronics.slug,
        )
        self.assertIn("final_price", response.data)
        self.assertIn("discount_amount", response.data)
        self.assertEqual(response.data["brand"], "Nexora")
        self.assertEqual(response.data["specifications"]["layout"], "US")
        self.assertIsNone(response.data["image_url"])

    def test_product_image_url_is_returned_as_absolute_url(self):
        self.keyboard.image = SimpleUploadedFile(
            "keyboard.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )
        self.keyboard.save()

        response = self.client.get(
            reverse(
                "product-detail",
                kwargs={"slug": self.keyboard.slug},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["image_url"].startswith("http"))

    def test_product_search_filter_works(self):
        response = self.client.get(
            reverse("product-list"),
            {"search": "headphones"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], self.headphones.slug)

    def test_product_brand_filter_supports_partial_match(self):
        response = self.client.get(
            reverse("product-list"),
            {"brand": "sound"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["slug"] for item in response.data["results"]],
            [self.headphones.slug],
        )

    def test_discount_filter_returns_only_products_with_active_discount(self):
        Discount.objects.create(
            product=self.keyboard,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("15.00"),
        )

        response = self.client.get(
            reverse("product-list"),
            {"has_discount": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["slug"] for item in response.data["results"]],
            [self.keyboard.slug],
        )

    def test_stock_range_filters_work(self):
        response = self.client.get(
            reverse("product-list"),
            {"min_stock": "6", "max_stock": "12"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["slug"] for item in response.data["results"]],
            [self.keyboard.slug],
        )

    def test_product_category_and_price_filters_work(self):
        response = self.client.get(
            reverse("product-list"),
            {
                "category": self.audio.slug,
                "min_price": "200",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], self.headphones.slug)

    def test_product_stock_filter_works(self):
        response = self.client.get(
            reverse("product-list"),
            {"in_stock": "false"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], self.out_of_stock.slug)

    def test_category_list_excludes_inactive_categories(self):
        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        names = {
            item["name"]
            for item in response.data["results"]
        }

        self.assertIn("Electronics", names)
        self.assertIn("Audio", names)
        self.assertNotIn("Hidden", names)

    def test_category_list_returns_nested_children(self):
        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        electronics = next(item for item in response.data["results"] if item["slug"] == self.electronics.slug)
        self.assertEqual(electronics["children"][0]["slug"], self.audio.slug)

    def test_root_category_filter_works(self):
        response = self.client.get(
            reverse("category-list"),
            {"root": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], self.electronics.slug)

    def test_public_product_api_is_read_only(self):
        response = self.client.post(
            reverse("product-list"),
            {
                "name": "Unauthorized Product",
                "sku": "UNAUTHORIZED-001",
                "price": "100.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
