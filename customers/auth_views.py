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

from .authentication import CookieJWTAuthentication
from .serializers import CustomerProfileSerializer


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

    def post(self, request):
        _enforce_csrf(request)

        serializer = TokenObtainPairSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

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
