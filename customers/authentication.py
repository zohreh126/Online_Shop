from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.db.models import Q
from unicodedata import normalize
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication


class CustomerAuthenticationBackend(BaseBackend):
    """Authenticate customers with either username or email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email") or kwargs.get("identifier")
        if not identifier or password is None:
            return None

        identifier = normalize("NFC", str(identifier)).strip()

        customer_model = get_user_model()
        customer = (
            customer_model.objects.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier),
                is_active=True,
            )
            .first()
        )

        if customer and customer.check_password(password):
            return customer

        return None

    def get_user(self, user_id):
        customer_model = get_user_model()
        try:
            return customer_model.objects.get(pk=user_id, is_active=True)
        except customer_model.DoesNotExist:
            return None


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)

        # پشتیبانی از Authorization: Bearer <token>
        if header is not None:
            return super().authenticate(request)

        # دریافت JWT از Cookie امن
        raw_token = request.COOKIES.get(
            settings.AUTH_COOKIE_ACCESS
        )

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(
            raw_token.encode("utf-8")
        )

        # درخواست‌های Cookie-based باید CSRF داشته باشند
        self.enforce_csrf(request)

        return (
            self.get_user(validated_token),
            validated_token,
        )

    @staticmethod
    def enforce_csrf(request):
        def dummy_get_response(request):
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(request)

        reason = check.process_view(
            request,
            None,
            (),
            {},
        )

        if reason:
            raise exceptions.PermissionDenied(
                f"CSRF Failed: {reason}"
            )
