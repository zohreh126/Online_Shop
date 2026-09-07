from django.urls import path
from rest_framework.routers import DefaultRouter

from .auth_views import (
    CSRFTokenView,
    CookieLoginView,
    CookieLogoutView,
    CookieRefreshView,
)
from .views import (
    AddressViewSet,
    CustomerProfileView,
    CustomerRegistrationView,
)


router = DefaultRouter()
router.register(
    "addresses",
    AddressViewSet,
    basename="customer-address",
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
]
