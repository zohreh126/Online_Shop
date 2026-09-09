import re

from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from .otp import _otp_key


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OTPAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.request_url = reverse("otp-request")
        self.verify_url = reverse("otp-verify")
        self.email = "otp@example.com"

    def request_code(self):
        response = self.client.post(
            self.request_url,
            {"email": self.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return re.search(r"(\d{6})", mail.outbox[-1].body).group(1)

    def test_otp_is_sent_and_only_hash_is_cached(self):
        code = self.request_code()
        payload = cache.get(_otp_key(self.email))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIsNotNone(payload)
        self.assertNotIn(code, payload["hash"])

    def test_valid_otp_is_verified_and_deleted(self):
        code = self.request_code()

        response = self.client.post(
            self.verify_url,
            {"email": self.email, "code": code},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["verified"])
        self.assertIsNone(cache.get(_otp_key(self.email)))

    def test_invalid_otp_is_rejected(self):
        self.request_code()

        response = self.client.post(
            self.verify_url,
            {"email": self.email, "code": "000000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_request_rate_limit_is_enforced(self):
        for _ in range(3):
            self.request_code()

        response = self.client.post(
            self.request_url,
            {"email": self.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
