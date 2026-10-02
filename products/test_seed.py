from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from .models import Category, Discount, DiscountCode, Product
from .serializers import ProductSerializer


class NexoraSeedCommandTests(TestCase):
    def test_seed_command_is_repeatable(self):
        call_command("seed_nexora", stdout=StringIO())
        first_category_count = Category.objects.count()
        first_product_count = Product.objects.count()
        first_discount_count = Discount.objects.count()
        first_code_count = DiscountCode.objects.count()

        call_command("seed_nexora", stdout=StringIO())

        self.assertEqual(Category.objects.count(), first_category_count)
        self.assertEqual(Product.objects.count(), first_product_count)
        self.assertEqual(Discount.objects.count(), first_discount_count)
        self.assertEqual(DiscountCode.objects.count(), first_code_count)
        product = Product.objects.get(sku="NX-FLUX-KB-001")
        self.assertEqual(product.brand, "Nexora")
        self.assertEqual(product.specifications["layout"], "75% / US")

    def test_seed_contains_expanded_nested_catalog(self):
        call_command("seed_nexora", stdout=StringIO())

        self.assertGreaterEqual(Product.objects.filter(is_active=True).count(), 26)
        self.assertGreaterEqual(Category.objects.filter(parent__isnull=False, is_active=True).count(), 9)
        self.assertGreaterEqual(Discount.objects.filter(is_active=True).count(), 5)
        self.assertTrue(Discount.objects.filter(ends_at__gt=timezone.now()).exists())
        self.assertTrue(DiscountCode.objects.filter(code="NEXORA10", is_active=True).exists())
        self.assertTrue(
            Category.objects.filter(
                parent__slug="audio",
                name="اسپیکر",
                is_active=True,
            ).exists()
        )

    def test_every_seeded_product_has_catalog_artwork(self):
        call_command("seed_nexora", stdout=StringIO())
        request = APIRequestFactory().get("/")

        for product in Product.objects.filter(sku__startswith="NX-"):
            serialized = ProductSerializer(product, context={"request": request}).data
            self.assertTrue(
                serialized["image_url"],
                msg=f"Missing artwork for {product.sku}",
            )

    def test_unseeded_product_without_upload_still_has_category_artwork(self):
        category = Category.objects.create(name="Audio accessories", slug="audio-accessories")
        product = Product.objects.create(
            name="Unseeded audio product",
            slug="unseeded-audio-product",
            sku="UNSEEDED-AUDIO-001",
            category=category,
            price="100000.00",
            stock_quantity=2,
        )
        request = APIRequestFactory().get("/")

        serialized = ProductSerializer(product, context={"request": request}).data

        self.assertIn("audio.svg", serialized["image_url"])
