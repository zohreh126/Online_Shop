from django.test import TestCase

from orders.models import Cart, CartItem, Order
from products.models import Category, Product

from .models import Address, Customer, Favorite, ProductWatch


class CustomerModelTests(TestCase):
    def test_delete_deactivates_customer(self):
        customer = Customer.objects.create_user(
            username="archive-user",
            email="archive-user@example.com",
            password="SecurePass#2026",
        )

        customer.delete()
        customer.refresh_from_db()

        self.assertFalse(customer.is_active)

    def test_delete_releases_identity_and_archives_customer_owned_data(self):
        customer = Customer.objects.create_user(
            username="reusable-user",
            email="reusable-user@example.com",
            password="SecurePass#2026",
        )
        category = Category.objects.create(
            name="Archive test category",
            slug="archive-test-category",
        )
        product = Product.objects.create(
            name="Archive test product",
            slug="archive-test-product",
            sku="ARCHIVE-001",
            category=category,
            price="100000.00",
            stock_quantity=3,
        )
        address = Address.objects.create(
            customer=customer,
            title="خانه",
            province="تهران",
            city="تهران",
            address_line="خیابان تست",
            postal_code="1234567890",
            recipient_name="کاربر تست",
            recipient_phone="09120000000",
            is_default=True,
        )
        favorite = Favorite.objects.create(customer=customer, product=product)
        watch = ProductWatch.objects.create(customer=customer, product=product)
        cart = Cart.objects.create(customer=customer)
        cart_item = CartItem.objects.create(cart=cart, product=product, quantity=1)
        order = Order.objects.create(
            customer=customer,
            shipping_title="خانه",
            shipping_province="تهران",
            shipping_city="تهران",
            shipping_address_line="خیابان تست",
            shipping_postal_code="1234567890",
            shipping_recipient_name="کاربر تست",
            shipping_recipient_phone="09120000000",
        )

        customer.delete()

        customer.refresh_from_db()
        address.refresh_from_db()
        favorite.refresh_from_db()
        watch.refresh_from_db()
        cart.refresh_from_db()
        cart_item.refresh_from_db()
        order.refresh_from_db()

        self.assertFalse(customer.is_active)
        self.assertFalse(customer.is_staff)
        self.assertTrue(customer.username.startswith("deleted-"))
        self.assertTrue(customer.email.endswith("@nexora.invalid"))
        self.assertFalse(address.is_active)
        self.assertFalse(address.is_default)
        self.assertFalse(favorite.is_active)
        self.assertFalse(watch.is_active)
        self.assertFalse(cart.is_active)
        self.assertEqual(cart_item.cart_id, cart.pk)
        self.assertEqual(order.customer_id, customer.pk)

        replacement = Customer.objects.create_user(
            username="reusable-user",
            email="reusable-user@example.com",
            password="SecurePass#2026",
        )
        self.assertTrue(replacement.is_active)
