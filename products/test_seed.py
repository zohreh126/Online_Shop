from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Category, Product


class NexoraSeedCommandTests(TestCase):
    def test_seed_command_is_repeatable(self):
        call_command("seed_nexora", stdout=StringIO())
        first_category_count = Category.objects.count()
        first_product_count = Product.objects.count()

        call_command("seed_nexora", stdout=StringIO())

        self.assertEqual(Category.objects.count(), first_category_count)
        self.assertEqual(Product.objects.count(), first_product_count)
        product = Product.objects.get(sku="NX-FLUX-KB-001")
        self.assertEqual(product.brand, "Nexora")
        self.assertEqual(product.specifications["layout"], "75% / US")
