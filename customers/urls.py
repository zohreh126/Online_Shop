from django.urls import path
from rest_framework.routers import DefaultRouter

from .auth_views import (
    CSRFTokenView,
    CookieLoginView,
    CookieLogoutView,
    CookieRefreshView,
    LoginOTPRequestView,
    LoginOTPVerifyView,
    PasswordChangeView,
    OTPRequestView,
    OTPVerifyView,
)
from .views import (
    AddressViewSet,
    CustomerProfileView,
    CustomerRegistrationView,
    FavoriteViewSet,
)


router = DefaultRouter()
router.register(
    "addresses",
    AddressViewSet,
    basename="customer-address",
)
router.register(
    "favorites",
    FavoriteViewSet,
    basename="customer-favorite",
)


urlpatterns = router.urls + [
    path(
        "csrf/",
        CSRFTokenView.as_view(),
        name="auth-csrf",
    ),
    path(
        "register/",
        CustomerRegistrationView.as_view(),
        name="customer-register",
    ),
    path(
        "login/",
        CookieLoginView.as_view(),
        name="auth-login",
    ),
    path("login/otp/request/", LoginOTPRequestView.as_view(), name="auth-login-otp-request"),
    path("login/otp/verify/", LoginOTPVerifyView.as_view(), name="auth-login-otp-verify"),
    path(
        "refresh/",
        CookieRefreshView.as_view(),
        name="auth-refresh",
    ),
    path(
        "logout/",
        CookieLogoutView.as_view(),
        name="auth-logout",
    ),
    path(
        "profile/",
        CustomerProfileView.as_view(),
        name="customer-profile",
    ),
    path(
        "password/change/",
        PasswordChangeView.as_view(),
        name="password-change",
    ),
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
]
