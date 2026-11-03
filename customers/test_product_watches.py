from decimal import Decimal

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Category, Discount, Product

from .models import Customer, ProductWatch
from .tasks import send_product_watch_notifications


class ProductWatchAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="watch-user",
            email="watch-user@example.com",
            password="SecurePass#2026",
        )
        self.other_customer = Customer.objects.create_user(
            username="other-watch-user",
            email="other-watch@example.com",
            password="SecurePass#2026",
        )
        category = Category.objects.create(name="Watch gadgets")
        self.product = Product.objects.create(
            name="Watch Keyboard",
            slug="watch-keyboard",
            sku="WATCH-KEYBOARD-001",
            category=category,
            price=Decimal("1200000.00"),
            stock_quantity=3,
        )
        self.url = reverse("customer-product-watch-list")

    def authenticate(self, customer=None):
        self.client.force_authenticate(customer or self.customer)

    def test_product_watches_require_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_subscribe_and_list_product_watch(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.pk,
                "notify_price_drop": True,
                "notify_restock": True,
                "target_price": "1000000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["product"]["sku"], self.product.sku)
        self.assertEqual(response.data["current_price"], Decimal("1200000.00"))
        watch = ProductWatch.objects.get(customer=self.customer, product=self.product)
        self.assertEqual(watch.last_seen_price, Decimal("1200000.00"))
        self.assertEqual(watch.last_seen_stock_quantity, 3)

        list_response = self.client.get(self.url)

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["results"]), 1)

    def test_watch_is_scoped_to_customer(self):
        ProductWatch.objects.create(
            customer=self.customer,
            product=self.product,
            last_seen_price=self.product.price,
            last_seen_stock_quantity=self.product.stock_quantity,
        )
        self.authenticate(self.other_customer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_delete_pauses_watch_and_post_restores_it(self):
        self.authenticate()
        create_response = self.client.post(
            self.url,
            {"product_id": self.product.pk},
            format="json",
        )
        watch_id = create_response.data["id"]

        delete_response = self.client.delete(
            reverse("customer-product-watch-detail", kwargs={"pk": watch_id}),
        )

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        watch = ProductWatch.objects.get(pk=watch_id)
        self.assertFalse(watch.is_active)
        self.assertEqual(self.client.get(self.url).data["results"], [])

        restore_response = self.client.post(
            self.url,
            {"product_id": self.product.pk, "notify_restock": False},
            format="json",
        )

        self.assertEqual(restore_response.status_code, status.HTTP_201_CREATED)
        watch.refresh_from_db()
        self.assertTrue(watch.is_active)
        self.assertFalse(watch.notify_restock)


class ProductWatchTaskTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="watch-task-user",
            email="watch-task@example.com",
            password="SecurePass#2026",
        )
        category = Category.objects.create(name="Task gadgets")
        self.product = Product.objects.create(
            name="Task Headphones",
            slug="task-headphones",
            sku="TASK-HEADPHONES-001",
            category=category,
            price=Decimal("900000.00"),
            stock_quantity=0,
        )

    def test_task_sends_combined_price_and_restock_alert(self):
        watch = ProductWatch.objects.create(
            customer=self.customer,
            product=self.product,
            last_seen_price=Decimal("1000000.00"),
            last_seen_stock_quantity=0,
        )
        Discount.objects.create(
            product=self.product,
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("200000.00"),
        )
        self.product.stock_quantity = 4
        self.product.save(update_fields=("stock_quantity", "updated_at"))

        result = send_product_watch_notifications()

        self.assertEqual(result, {"checked": 1, "sent": 1, "failed": 0})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Task Headphones", mail.outbox[0].subject)
        self.assertIn("کاهش قیمت", mail.outbox[0].body)
        self.assertIn("موجودی محصول دوباره", mail.outbox[0].body)
        watch.refresh_from_db()
        self.assertEqual(watch.last_seen_price, Decimal("700000.00"))
        self.assertEqual(watch.last_seen_stock_quantity, 4)
        self.assertIsNotNone(watch.last_price_notified_at)
        self.assertIsNotNone(watch.last_restock_notified_at)

    def test_task_updates_baseline_without_email_when_threshold_is_not_reached(self):
        watch = ProductWatch.objects.create(
            customer=self.customer,
            product=self.product,
            target_price=Decimal("700000.00"),
            last_seen_price=Decimal("1000000.00"),
            last_seen_stock_quantity=0,
        )
        self.product.price = Decimal("800000.00")
        self.product.save(update_fields=("price", "updated_at"))

        result = send_product_watch_notifications()

        self.assertEqual(result["sent"], 0)
        self.assertEqual(len(mail.outbox), 0)
        watch.refresh_from_db()
        self.assertEqual(watch.last_seen_price, Decimal("800000.00"))
