from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Customer
from orders.models import Order, OrderItem

from .models import (
    Category,
    Discount,
    Product,
    ProductQuestion,
    ProductReview,
    ProductReviewHelpfulVote,
)


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
        self.assertIsNone(response.data["discount_ends_at"])
        self.assertEqual(response.data["brand"], "Nexora")
        self.assertEqual(response.data["specifications"]["layout"], "US")
        self.assertIsNone(response.data["image_url"])
        self.assertEqual(response.data["rating_average"], 0.0)
        self.assertEqual(response.data["rating_count"], 0)
        self.assertIsNone(response.data["discount_type"])
        self.assertIsNone(response.data["discount_value"])

    def test_product_reviews_are_public(self):
        customer = Customer.objects.create_user(
            username="public-reviewer",
            email="public-reviewer@example.com",
            password="Strong-password-123",
        )
        ProductReview.objects.create(
            product=self.keyboard,
            customer=customer,
            rating=4,
            title="Solid choice",
            body="The keyboard feels reliable.",
        )

        response = self.client.get(
            reverse("product-reviews", kwargs={"slug": self.keyboard.slug})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["average"], 4.0)
        self.assertEqual(
            response.data["rating_distribution"],
            {"5": 0, "4": 1, "3": 0, "2": 0, "1": 0},
        )
        self.assertEqual(response.data["results"][0]["customer_name"], "public-reviewer")
        self.assertFalse(response.data["results"][0]["is_mine"])
        self.assertFalse(response.data["results"][0]["is_verified_purchase"])
        self.assertEqual(response.data["results"][0]["helpful_count"], 0)
        self.assertFalse(response.data["results"][0]["helpful_by_me"])

    def test_product_reviews_support_public_sorting(self):
        low_review = ProductReview.objects.create(
            product=self.keyboard,
            customer=Customer.objects.create_user(
                username="sort-low",
                email="sort-low@example.com",
                password="Strong-password-123",
            ),
            rating=2,
            body="A low rating review.",
        )
        high_review = ProductReview.objects.create(
            product=self.keyboard,
            customer=Customer.objects.create_user(
                username="sort-high",
                email="sort-high@example.com",
                password="Strong-password-123",
            ),
            rating=5,
            body="A high rating review.",
        )
        useful_review = ProductReview.objects.create(
            product=self.keyboard,
            customer=Customer.objects.create_user(
                username="sort-useful",
                email="sort-useful@example.com",
                password="Strong-password-123",
            ),
            rating=4,
            body="A useful review.",
        )
        for index in range(2):
            ProductReviewHelpfulVote.objects.create(
                review=useful_review,
                customer=Customer.objects.create_user(
                    username=f"sort-voter-{index}",
                    email=f"sort-voter-{index}@example.com",
                    password="Strong-password-123",
                ),
            )

        highest_response = self.client.get(
            reverse("product-reviews", kwargs={"slug": self.keyboard.slug}),
            {"sort": "highest"},
        )
        helpful_response = self.client.get(
            reverse("product-reviews", kwargs={"slug": self.keyboard.slug}),
            {"sort": "helpful"},
        )

        self.assertEqual(highest_response.data["results"][0]["id"], high_review.pk)
        self.assertEqual(helpful_response.data["results"][0]["id"], useful_review.pk)
        self.assertIn(low_review.pk, [item["id"] for item in highest_response.data["results"]])

    def test_writing_product_review_requires_authentication(self):
        response = self.client.post(
            reverse("product-reviews", kwargs={"slug": self.keyboard.slug}),
            {"rating": 5, "body": "Great keyboard."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_customer_can_create_and_update_one_review(self):
        customer = Customer.objects.create_user(
            username="review-writer",
            email="review-writer@example.com",
            password="Strong-password-123",
        )
        self.client.force_authenticate(user=customer)
        url = reverse("product-reviews", kwargs={"slug": self.keyboard.slug})

        create_response = self.client.post(
            url,
            {
                "rating": 5,
                "title": "Excellent",
                "body": "This is a very good keyboard.",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(create_response.data["review"]["is_mine"])
        self.assertEqual(create_response.data["count"], 1)
        self.assertEqual(create_response.data["average"], 5.0)
        self.assertEqual(create_response.data["rating_distribution"]["5"], 1)

        update_response = self.client.post(
            url,
            {
                "rating": 3,
                "title": "Updated",
                "body": "It is good, but not perfect.",
            },
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["review"]["rating"], 3)
        self.assertEqual(update_response.data["count"], 1)
        self.assertEqual(update_response.data["average"], 3.0)
        self.assertEqual(update_response.data["rating_distribution"]["3"], 1)
        self.assertEqual(
            ProductReview.objects.filter(
                product=self.keyboard,
                customer=customer,
            ).count(),
            1,
        )

    def test_review_from_paid_order_is_marked_as_verified_purchase(self):
        customer = Customer.objects.create_user(
            username="verified-reviewer",
            email="verified-reviewer@example.com",
            password="Strong-password-123",
        )
        order = Order.objects.create(
            customer=customer,
            status=Order.Status.DELIVERED,
            payment_status=Order.PaymentStatus.PAID,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            shipping_title="Home",
            shipping_province="Tehran",
            shipping_city="Tehran",
            shipping_address_line="A test address",
            shipping_postal_code="1234567890",
            shipping_recipient_name="Verified Reviewer",
            shipping_recipient_phone="09120000000",
        )
        OrderItem.objects.create(
            order=order,
            product=self.keyboard,
            product_name=self.keyboard.name,
            product_sku=self.keyboard.sku,
            unit_price=self.keyboard.price,
            unit_discount=Decimal("0.00"),
            quantity=1,
        )
        ProductReview.objects.create(
            product=self.keyboard,
            customer=customer,
            rating=5,
            body="I bought and tested this keyboard.",
        )

        response = self.client.get(
            reverse("product-reviews", kwargs={"slug": self.keyboard.slug})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["results"][0]["is_verified_purchase"])

    def test_authenticated_customer_can_toggle_review_helpful_vote(self):
        author = Customer.objects.create_user(
            username="review-author",
            email="review-author@example.com",
            password="Strong-password-123",
        )
        voter = Customer.objects.create_user(
            username="review-voter",
            email="review-voter@example.com",
            password="Strong-password-123",
        )
        review = ProductReview.objects.create(
            product=self.keyboard,
            customer=author,
            rating=5,
            body="A detailed and useful review.",
        )
        url = reverse(
            "product-review-helpful",
            kwargs={"slug": self.keyboard.slug, "review_id": review.pk},
        )

        anonymous_response = self.client.post(url, format="json")
        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=voter)
        first_response = self.client.post(url, format="json")
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertTrue(first_response.data["helpful"])
        self.assertEqual(first_response.data["helpful_count"], 1)

        review_response = self.client.get(
            reverse("product-reviews", kwargs={"slug": self.keyboard.slug})
        )
        self.assertTrue(review_response.data["results"][0]["helpful_by_me"])
        self.assertEqual(review_response.data["results"][0]["helpful_count"], 1)

        second_response = self.client.post(url, format="json")
        self.assertFalse(second_response.data["helpful"])
        self.assertEqual(second_response.data["helpful_count"], 0)
        self.assertFalse(ProductReviewHelpfulVote.objects.exists())

    def test_product_questions_are_public_and_include_answers(self):
        customer = Customer.objects.create_user(
            username="question-author",
            email="question-author@example.com",
            password="Strong-password-123",
            first_name="Question",
            last_name="Author",
        )
        question = ProductQuestion.objects.create(
            product=self.keyboard,
            customer=customer,
            question="Does this keyboard support USB-C?",
            answer="Yes, it includes a USB-C connection.",
            answered_at=timezone.now(),
        )

        response = self.client.get(
            reverse("product-questions", kwargs={"slug": self.keyboard.slug})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], question.pk)
        self.assertEqual(response.data["results"][0]["customer_name"], "Question Author")
        self.assertEqual(
            response.data["results"][0]["answer"],
            "Yes, it includes a USB-C connection.",
        )
        self.assertFalse(response.data["results"][0]["is_mine"])

    def test_writing_product_question_requires_authentication(self):
        response = self.client.post(
            reverse("product-questions", kwargs={"slug": self.keyboard.slug}),
            {"question": "Is this suitable for everyday use?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_customer_can_ask_product_question(self):
        customer = Customer.objects.create_user(
            username="question-writer",
            email="question-writer@example.com",
            password="Strong-password-123",
        )
        self.client.force_authenticate(user=customer)

        response = self.client.post(
            reverse("product-questions", kwargs={"slug": self.keyboard.slug}),
            {"question": "  Is   this   good for travel?  "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["count"], 1)
        self.assertTrue(response.data["question"]["is_mine"])
        self.assertEqual(response.data["question"]["question"], "Is this good for travel?")
        self.assertTrue(
            ProductQuestion.objects.filter(
                product=self.keyboard,
                customer=customer,
                question="Is this good for travel?",
            ).exists()
        )

    def test_only_staff_can_answer_product_question(self):
        customer = Customer.objects.create_user(
            username="question-customer",
            email="question-customer@example.com",
            password="Strong-password-123",
        )
        question = ProductQuestion.objects.create(
            product=self.keyboard,
            customer=customer,
            question="Can I use this with a laptop?",
        )
        url = reverse(
            "product-answer-question",
            kwargs={"slug": self.keyboard.slug, "question_id": question.pk},
        )

        self.client.force_authenticate(user=customer)
        customer_response = self.client.patch(
            url,
            {"answer": "Customer answer should not be accepted."},
            format="json",
        )
        self.assertEqual(customer_response.status_code, status.HTTP_403_FORBIDDEN)

        staff = Customer.objects.create_superuser(
            username="question-admin",
            email="question-admin@example.com",
            password="Strong-password-123",
        )
        self.client.force_authenticate(user=staff)
        staff_response = self.client.patch(
            url,
            {"answer": "Yes, it works with a laptop."},
            format="json",
        )

        self.assertEqual(staff_response.status_code, status.HTTP_200_OK)
        self.assertEqual(staff_response.data["answer"], "Yes, it works with a laptop.")
        question.refresh_from_db()
        self.assertEqual(question.answer, "Yes, it works with a laptop.")
        self.assertIsNotNone(question.answered_at)

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

    def test_product_discount_metadata_is_exposed_for_storefront_badges(self):
        Discount.objects.create(
            product=self.keyboard,
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("15.00"),
            ends_at=timezone.now() + timedelta(days=2),
        )

        response = self.client.get(
            reverse(
                "product-detail",
                kwargs={"slug": self.keyboard.slug},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["discount_type"], Discount.DiscountType.PERCENTAGE)
        self.assertEqual(Decimal(str(response.data["discount_value"])), Decimal("15.00"))
        self.assertIsNotNone(response.data["discount_ends_at"])

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
