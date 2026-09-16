from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Customer, SiteFeedback


class SiteFeedbackAPITests(APITestCase):
    def test_guest_can_submit_feedback_with_normalized_comment(self):
        response = self.client.post(
            reverse("site-feedback"),
            {
                "rating": 5,
                "comment": "  تجربهٔ  خیلی خوب   بود.  ",
                "page": "/",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        feedback = SiteFeedback.objects.get()
        self.assertIsNone(feedback.customer)
        self.assertEqual(feedback.comment, "تجربهٔ خیلی خوب بود.")
        self.assertEqual(feedback.page, "/")
        self.assertTrue(feedback.session_key)

    def test_authenticated_feedback_is_linked_to_customer(self):
        customer = Customer.objects.create_user(
            username="feedback-user",
            email="feedback-user@example.com",
            password="Strong-password-123",
        )
        self.client.force_authenticate(user=customer)

        response = self.client.post(
            reverse("site-feedback"),
            {"rating": 4, "comment": "پیشنهاد من این است."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        feedback = SiteFeedback.objects.get()
        self.assertEqual(feedback.customer, customer)
        self.assertEqual(feedback.page, "/api/v1/auth/feedback/")

    def test_feedback_rating_must_be_between_one_and_five(self):
        response = self.client.post(
            reverse("site-feedback"),
            {"rating": 6},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rating", response.data)

    def test_feedback_delete_is_soft(self):
        feedback = SiteFeedback.objects.create(rating=3, comment="Needs polish.")

        feedback.delete()
        feedback.refresh_from_db()

        self.assertFalse(feedback.is_active)

    def test_guest_can_read_active_public_feedback_without_authentication(self):
        customer = Customer.objects.create_user(
            username="public-feedback-user",
            email="public-feedback@example.com",
            password="Strong-password-123",
            first_name="Zohreh",
        )
        SiteFeedback.objects.create(
            customer=customer,
            rating=5,
            comment="Very smooth shopping.",
            page="/",
        )
        SiteFeedback.objects.create(
            rating=1,
            comment="Hidden feedback.",
            page="/",
            is_active=False,
        )
        SiteFeedback.objects.create(
            rating=4,
            comment="Another page.",
            page="/contact/",
        )

        response = self.client.get(reverse("site-feedback"), {"page_path": "/"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["customer_name"], "Zohreh")
        self.assertEqual(response.data["results"][0]["rating"], 5)
        self.assertNotContains(response, "Hidden feedback")
