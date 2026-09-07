from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Customer


class CookieJWTAuthAPITests(APITestCase):
    password = "SecurePass#2026"

    def setUp(self):
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
