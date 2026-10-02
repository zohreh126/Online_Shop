from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
import re

from .models import Customer


class CookieJWTAuthAPITests(APITestCase):
    password = "SecurePass#2026"

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

        self.customer = Customer.objects.create_user(
            username="authuser",
            email="authuser@example.com",
            password=self.password,
        )

        self.csrf_url = reverse("auth-csrf")
        self.login_url = reverse("auth-login")
        self.refresh_url = reverse("auth-refresh")
        self.logout_url = reverse("auth-logout")
        self.profile_url = reverse("customer-profile")

    def get_csrf_token(self):
        response = self.client.get(self.csrf_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        return self.client.cookies[
            settings.CSRF_COOKIE_NAME
        ].value

    def login(self):
        csrf_token = self.get_csrf_token()

        self.client.credentials(
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        return self.client.post(
            self.login_url,
            {
                "username": "authuser",
                "password": self.password,
            },
            format="json",
        )

    def test_csrf_endpoint_sets_readable_cookie(self):
        response = self.client.get(self.csrf_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        csrf_cookie = response.cookies.get(
            settings.CSRF_COOKIE_NAME
        )

        self.assertIsNotNone(csrf_cookie)
        self.assertFalse(csrf_cookie["httponly"])

    def test_login_requires_csrf(self):
        self.get_csrf_token()
        self.client.credentials()

        response = self.client.post(
            self.login_url,
            {
                "username": "authuser",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_login_sets_http_only_auth_cookies(self):
        response = self.login()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)

        access_cookie = response.cookies.get(
            settings.AUTH_COOKIE_ACCESS
        )
        refresh_cookie = response.cookies.get(
            settings.AUTH_COOKIE_REFRESH
        )

        self.assertIsNotNone(access_cookie)
        self.assertIsNotNone(refresh_cookie)
        self.assertTrue(access_cookie["httponly"])
        self.assertTrue(refresh_cookie["httponly"])
        self.assertEqual(
            response.data["user"]["username"],
            "authuser",
        )

    def test_invalid_credentials_are_rejected(self):
        csrf_token = self.get_csrf_token()

        self.client.credentials(
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        response = self.client.post(
            self.login_url,
            {
                "username": "authuser",
                "password": "WrongPassword#2026",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(response.data["error_code"], "invalid_credentials")

    def test_login_accepts_persian_digits_in_password(self):
        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)

        response = self.client.post(
            self.login_url,
            {
                "identifier": "authuser",
                "password": "SecurePass#۲۰۲۶",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "authuser")

    def test_login_accepts_email_as_identifier(self):
        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)

        response = self.client.post(
            self.login_url,
            {
                "email": "authuser@example.com",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "authuser@example.com")

    def test_login_ignores_soft_deleted_duplicate_identity(self):
        archived = Customer.objects.create_user(
            username="archived-login",
            email="login-reuse@example.com",
            password="OldPass#2026",
        )
        archived.delete()
        active = Customer.objects.create_user(
            username="active-login",
            email="login-reuse@example.com",
            password="SecurePass#2026",
        )

        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        response = self.client.post(
            self.login_url,
            {
                "identifier": active.email,
                "password": "SecurePass#2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], active.pk)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_two_step_login_sends_otp_and_sets_cookies_after_verification(self):
        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)

        request_response = self.client.post(
            reverse("auth-login-otp-request"),
            {"identifier": "authuser", "password": self.password},
            format="json",
        )

        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r"(\d{6})", mail.outbox[0].body).group(1)

        verify_response = self.client.post(
            reverse("auth-login-otp-verify"),
            {"email": self.customer.email, "code": code},
            format="json",
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_response.data["user"]["role"], "")
        self.assertIsNotNone(verify_response.cookies.get(settings.AUTH_COOKIE_ACCESS))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_customer_can_request_otp_with_email_only(self):
        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)

        response = self.client.post(
            reverse("auth-login-otp-request"),
            {"email": self.customer.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.customer.email)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_login_otp_rate_limit_returns_a_clear_response(self):
        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        url = reverse("auth-login-otp-request")

        for _ in range(3):
            response = self.client.post(
                url,
                {"email": self.customer.email},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            url,
            {"email": self.customer.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["error_code"], "otp_rate_limited")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_staff_cannot_use_customer_email_otp_login(self):
        staff = Customer.objects.create_superuser(
            username="otp-admin",
            email="otp-admin@example.com",
            password=self.password,
        )
        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)

        response = self.client.post(
            reverse("auth-login-otp-request"),
            {"email": staff.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(mail.outbox)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_two_step_login_rejects_invalid_code(self):
        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        self.client.post(
            reverse("auth-login-otp-request"),
            {"identifier": self.customer.email, "password": self.password},
            format="json",
        )

        response = self.client.post(
            reverse("auth-login-otp-verify"),
            {"email": self.customer.email, "code": "000000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_and_login_support_persian_username(self):
        registration_response = self.client.post(
            reverse("customer-register"),
            {
                "username": "سعید",
                "email": "saeed@example.com",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
        )
        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)

        csrf_token = self.get_csrf_token()
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        login_response = self.client.post(
            self.login_url,
            {"identifier": "سعید", "password": self.password},
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(login_response.data["user"]["username"], "سعید")

    def test_password_change_updates_password(self):
        self.login()
        csrf_token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)

        response = self.client.post(
            reverse("password-change"),
            {
                "current_password": self.password,
                "new_password": "NewSecurePass#2026",
                "new_password_confirm": "NewSecurePass#2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("NewSecurePass#2026"))

    def test_password_change_rejects_wrong_current_password(self):
        self.login()
        csrf_token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)

        response = self.client.post(
            reverse("password-change"),
            {
                "current_password": "WrongPassword#2026",
                "new_password": "NewSecurePass#2026",
                "new_password_confirm": "NewSecurePass#2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_requires_authentication(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_cookie_authentication_allows_profile_access(self):
        login_response = self.login()

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        response = self.client.get(self.profile_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["username"],
            "authuser",
        )

    def test_refresh_rotates_refresh_cookie(self):
        login_response = self.login()

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        old_refresh = self.client.cookies[
            settings.AUTH_COOKIE_REFRESH
        ].value

        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        new_refresh = response.cookies[
            settings.AUTH_COOKIE_REFRESH
        ].value

        self.assertNotEqual(old_refresh, new_refresh)

    def test_refresh_without_cookie_is_rejected(self):
        csrf_token = self.get_csrf_token()

        self.client.credentials(
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_clears_auth_cookies(self):
        login_response = self.login()

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        response = self.client.post(
            self.logout_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.cookies[
                settings.AUTH_COOKIE_ACCESS
            ].value,
            "",
        )
        self.assertEqual(
            response.cookies[
                settings.AUTH_COOKIE_REFRESH
            ].value,
            "",
        )
