from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Category, Discount, DiscountCode, Product


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
        self.assertTrue(DiscountCode.objects.filter(code="NEXORA10", is_active=True).exists())
        self.assertTrue(
            Category.objects.filter(
                parent__slug="audio",
                name="اسپیکر",
                is_active=True,
            ).exists()
        )
