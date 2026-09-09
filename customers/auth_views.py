from django.conf import settings
from django.middleware.csrf import get_token
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
from orders.cart_services import merge_guest_cart
from .otp import request_otp, verify_otp
from .serializers import (
    CustomerProfileSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordChangeSerializer,
)
from rest_framework.exceptions import AuthenticationFailed


REFRESH_COOKIE_PATH = "/api/v1/auth/"


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
            login_data["username"] = identifier

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

        merge_guest_cart(request, serializer.user)

        tokens = serializer.validated_data
        response = Response(
            {
                "detail": "Login successful.",
                "user": CustomerProfileSerializer(
                    serializer.user
                ).data,
            },
            status=status.HTTP_200_OK,
        )

        _set_auth_cookie(
            response,
            settings.AUTH_COOKIE_ACCESS,
            tokens["access"],
            int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
            "/",
        )
        _set_auth_cookie(
            response,
            settings.AUTH_COOKIE_REFRESH,
            tokens["refresh"],
            int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
            REFRESH_COOKIE_PATH,
        )
        _set_csrf_cookie(response, get_token(request))

        return response


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

        refresh_token = request.COOKIES.get(
            settings.AUTH_COOKIE_REFRESH
        )

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response(
            {"detail": "Logout successful."},
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

        return Response(
            {"detail": "Email verified successfully.", "verified": True},
            status=status.HTTP_200_OK,
        )
