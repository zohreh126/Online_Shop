from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Category, Discount, DiscountCode, Product


class CategoryModelTests(TestCase):
    def test_slug_is_generated_automatically(self):
        category = Category.objects.create(
            name="Mobile Phones",
        )

        self.assertEqual(category.slug, "mobile-phones")

    def test_category_cannot_be_its_own_parent(self):
        category = Category.objects.create(
            name="Electronics",
        )

        category.parent = category

        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_delete_deactivates_category(self):
        category = Category.objects.create(name="To archive")

        category.delete()
        category.refresh_from_db()

        self.assertFalse(category.is_active)


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
        )

    def create_product(self, **kwargs):
        defaults = {
            "name": "Test Product",
            "sku": "TEST-001",
            "category": self.category,
            "price": Decimal("100.00"),
            "stock_quantity": 10,
        }

        defaults.update(kwargs)

        if "name" not in kwargs:
            defaults["name"] = f"Test Product {defaults['sku']}"

        return Product.objects.create(**defaults)


    def test_product_slug_is_generated(self):
        product = self.create_product(
            name="Wireless Headphones",
        )

        self.assertEqual(product.slug, "wireless-headphones")

    def test_active_queryset_returns_only_active_products(self):
        active_product = self.create_product(
            sku="ACTIVE-001",
            is_active=True,
        )

        self.create_product(
            sku="INACTIVE-001",
            is_active=False,
        )

        self.assertEqual(
            list(Product.objects.active()),
            [active_product],
        )

    def test_in_stock_queryset_excludes_zero_stock_products(self):
        available_product = self.create_product(
            sku="AVAILABLE-001",
            stock_quantity=5,
        )

        self.create_product(
            sku="EMPTY-001",
            stock_quantity=0,
        )

        self.assertEqual(
            list(Product.objects.in_stock()),
            [available_product],
        )

    def test_is_in_stock_property(self):
        product = self.create_product(
            stock_quantity=3,
        )

        self.assertTrue(product.is_in_stock)

        product.stock_quantity = 0

        self.assertFalse(product.is_in_stock)

    def test_delete_deactivates_product(self):
        product = self.create_product()

        product.delete()
        product.refresh_from_db()

        self.assertFalse(product.is_active)


class DiscountModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
        )

        self.product = Product.objects.create(
            name="Laptop",
            sku="LAPTOP-001",
            category=self.category,
            price=Decimal("1000.00"),
            stock_quantity=5,
        )

    def test_percentage_discount_is_calculated(self):
        discount = Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
        )

        self.assertEqual(
            discount.calculate_discount(Decimal("1000.00")),
            Decimal("100.00"),
        )

    def test_percentage_discount_respects_maximum_amount(self):
        discount = Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("20.00"),
            max_amount=Decimal("50.00"),
        )

        self.assertEqual(
            discount.calculate_discount(Decimal("1000.00")),
            Decimal("50.00"),
        )

    def test_fixed_discount_is_calculated(self):
        discount = Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("75.00"),
        )

        self.assertEqual(
            discount.calculate_discount(Decimal("1000.00")),
            Decimal("75.00"),
        )

    def test_percentage_discount_cannot_exceed_one_hundred(self):
        discount = Discount(
            product=self.product,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("101.00"),
        )

        with self.assertRaises(ValidationError):
            discount.full_clean()

    def test_inactive_discount_returns_zero(self):
        discount = Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
            is_active=False,
        )

        self.assertEqual(
            discount.calculate_discount(Decimal("1000.00")),
            Decimal("0.00"),
        )

    def test_expired_discount_returns_zero(self):
        discount = Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
            ends_at=timezone.now() - timedelta(days=1),
        )

        self.assertEqual(
            discount.calculate_discount(Decimal("1000.00")),
            Decimal("0.00"),
        )

    def test_delete_deactivates_discount(self):
        discount = Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("10.00"),
        )

        discount.delete()
        discount.refresh_from_db()

        self.assertFalse(discount.is_active)


class DiscountCodeModelTests(TestCase):
    def test_code_is_normalized_to_uppercase(self):
        discount_code = DiscountCode.objects.create(
            code=" summer10 ",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
        )

        self.assertEqual(discount_code.code, "SUMMER10")

    def test_discount_code_respects_minimum_order_amount(self):
        discount_code = DiscountCode.objects.create(
            code="MIN100",
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("20.00"),
            minimum_order_amount=Decimal("100.00"),
        )

        self.assertEqual(
            discount_code.calculate_discount(Decimal("50.00")),
            Decimal("0.00"),
        )

        self.assertEqual(
            discount_code.calculate_discount(Decimal("150.00")),
            Decimal("20.00"),
        )

    def test_discount_code_usage_limit(self):
        discount_code = DiscountCode.objects.create(
            code="LIMITED",
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("20.00"),
            usage_limit=1,
            used_count=1,
        )

        self.assertFalse(discount_code.is_valid_now)

    def test_discount_code_percentage_maximum_amount(self):
        discount_code = DiscountCode.objects.create(
            code="PERCENT20",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("20.00"),
            max_amount=Decimal("30.00"),
        )

        self.assertEqual(
            discount_code.calculate_discount(Decimal("500.00")),
            Decimal("30.00"),
        )

    def test_delete_deactivates_discount_code(self):
        discount_code = DiscountCode.objects.create(
            code="ARCHIVE10",
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("10.00"),
        )

        discount_code.delete()
        discount_code.refresh_from_db()

        self.assertFalse(discount_code.is_active)
