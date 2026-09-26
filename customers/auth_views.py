from django.conf import settings
from django.middleware.csrf import get_token
from django.core.cache import cache
from django.contrib.auth import authenticate
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .authentication import CookieJWTAuthentication
from orders.cart_services import clear_guest_cart, merge_guest_cart
from .otp import OTPDeliveryError, request_otp, verify_otp
from .serializers import (
    CustomerProfileSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordChangeSerializer,
)
from .models import Customer
from rest_framework.exceptions import AuthenticationFailed
from unicodedata import normalize


REFRESH_COOKIE_PATH = "/api/v1/auth/"
LOGIN_OTP_TTL = 5 * 60


def _login_otp_key(email):
    return f"nexora:login-otp:{email}"


def _set_auth_cookie(response, name, value, max_age, path):
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        path=path,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def _set_csrf_cookie(response, token):
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        path="/",
        secure=settings.CSRF_COOKIE_SECURE,
        httponly=False,
        samesite=settings.CSRF_COOKIE_SAMESITE,
    )


def _enforce_csrf(request):
    CookieJWTAuthentication.enforce_csrf(request)


def _login_response(request, user):
    merge_guest_cart(request, user)
    refresh = RefreshToken.for_user(user)
    response = Response(
        {
            "detail": "Login successful.",
            "user": CustomerProfileSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )
    _set_auth_cookie(response, settings.AUTH_COOKIE_ACCESS, str(refresh.access_token), int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()), "/")
    _set_auth_cookie(response, settings.AUTH_COOKIE_REFRESH, str(refresh), int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()), REFRESH_COOKIE_PATH)
    _set_csrf_cookie(response, get_token(request))
    return response


class CSRFTokenView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        token = get_token(request)
        response = Response(
            {"detail": "CSRF cookie set."},
            status=status.HTTP_200_OK,
        )
        _set_csrf_cookie(response, token)
        return response


class CookieLoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(
        request=inline_serializer(
            name="CookieLoginRequest",
            fields={
                "username": serializers.CharField(),
                "password": serializers.CharField(),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        _enforce_csrf(request)

        login_data = request.data.copy()
        identifier = login_data.get("identifier") or login_data.get("email")
        if identifier and not login_data.get("username"):
            login_data["username"] = normalize("NFC", str(identifier)).strip()

        serializer = TokenObtainPairSerializer(
            data=login_data,
            context={"request": request},
        )

        try:
            serializer.is_valid(raise_exception=True)
        except AuthenticationFailed as exc:
            return Response(
                {"detail": exc.detail},
                status=status.HTTP_401_UNAUTHORIZED,
                headers={
                    "WWW-Authenticate": 'Bearer realm="api"',
                },
            )

        return _login_response(request, serializer.user)


class LoginOTPRequestView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(
        request=inline_serializer(
            name="LoginOTPRequest",
            fields={
                "email": serializers.EmailField(required=False),
                "identifier": serializers.CharField(required=False),
                "password": serializers.CharField(required=False),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        _enforce_csrf(request)

        raw_email = request.data.get("email")
        raw_identifier = request.data.get("identifier")
        password = request.data.get("password")
        identifier = normalize(
            "NFC",
            str(raw_identifier or raw_email or ""),
        ).strip()

        # The customer-facing OTP flow intentionally needs only the email.
        # Keep identifier + password support for existing API clients while
        # preventing staff accounts from using the customer login route.
        if raw_email or (identifier and "@" in identifier and not password):
            email = normalize("NFC", str(raw_email or identifier)).strip().lower()
            user = (
                Customer.objects.filter(
                    email__iexact=email,
                    is_active=True,
                )
                .first()
            )
        else:
            user = authenticate(request, username=identifier, password=password)

        if user is None:
            return Response({"detail": "نام کاربری/ایمیل یا رمز عبور صحیح نیست."}, status=status.HTTP_401_UNAUTHORIZED)

        if user.is_staff or user.is_superuser or user.role:
            return Response(
                {"detail": "ورود با کد ایمیل فقط برای مشتریان فعال است."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            request_otp(user.email)
        except OTPDeliveryError:
            return Response(
                {
                    "error_code": "email_delivery_failed",
                    "detail": "کد ورود ارسال نشد؛ تنظیمات ایمیل فروشگاه را بررسی کن.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        cache.set(_login_otp_key(user.email), user.pk, timeout=LOGIN_OTP_TTL)
        return Response({"detail": "Verification code sent.", "email": user.email}, status=status.HTTP_200_OK)


class LoginOTPVerifyView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(request=inline_serializer(name="LoginOTPVerifyRequest", fields={"email": serializers.EmailField(), "code": serializers.RegexField(regex=r"^\d{6}$")}), responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})
    def post(self, request):
        _enforce_csrf(request)
        email = normalize("NFC", str(request.data.get("email", ""))).strip().lower()
        code = str(request.data.get("code", "")).strip()
        user_id = cache.get(_login_otp_key(email))
        if not user_id:
            return Response({"detail": "کد ورود منقضی شده است؛ دوباره درخواست کد بده."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            verify_otp(email, code)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        user = CustomerProfileSerializer.Meta.model.objects.filter(pk=user_id, is_active=True).first()
        cache.delete(_login_otp_key(email))
        if user is None:
            return Response({"detail": "حساب کاربری فعال پیدا نشد."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=("email_verified",))
        return _login_response(request, user)


class CookieRefreshView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        _enforce_csrf(request)

        refresh_token = request.COOKIES.get(
            settings.AUTH_COOKIE_REFRESH
        )

        if not refresh_token:
            return Response(
                {"detail": "Refresh token cookie is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = TokenRefreshSerializer(
            data={"refresh": refresh_token}
        )
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data
        response = Response(
            {"detail": "Token refreshed successfully."},
            status=status.HTTP_200_OK,
        )

        _set_auth_cookie(
            response,
            settings.AUTH_COOKIE_ACCESS,
            tokens["access"],
            int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
            "/",
        )

        if "refresh" in tokens:
            _set_auth_cookie(
                response,
                settings.AUTH_COOKIE_REFRESH,
                tokens["refresh"],
                int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
                REFRESH_COOKIE_PATH,
            )

        _set_csrf_cookie(response, get_token(request))

        return response


class CookieLogoutView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        _enforce_csrf(request)
        clear_guest_cart(request)

        refresh_token = request.COOKIES.get(
            settings.AUTH_COOKIE_REFRESH
        )

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response(
            {"detail": "Logout successful.", "clear_client_state": True},
            status=status.HTTP_200_OK,
        )

        response.delete_cookie(
            settings.AUTH_COOKIE_ACCESS,
            path="/",
        )
        response.delete_cookie(
            settings.AUTH_COOKIE_REFRESH,
            path=REFRESH_COOKIE_PATH,
        )

        return response


class PasswordChangeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class OTPRequestView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(request=OTPRequestSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_otp(serializer.validated_data["email"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except OTPDeliveryError:
            return Response(
                {
                    "error_code": "email_delivery_failed",
                    "detail": "کد تأیید ارسال نشد؛ تنظیمات ایمیل فروشگاه را بررسی کن.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"detail": "Verification code sent."},
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(request=OTPVerifySerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verify_otp(
                serializer.validated_data["email"],
                serializer.validated_data["code"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .models import Customer
        Customer.objects.filter(email=serializer.validated_data["email"]).update(email_verified=True)

        return Response(
            {"detail": "Email verified successfully.", "verified": True},
            status=status.HTTP_200_OK,
        )
