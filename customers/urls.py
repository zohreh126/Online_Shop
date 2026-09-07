from django.urls import path

from .auth_views import (
    CSRFTokenView,
    CookieLoginView,
    CookieLogoutView,
    CookieRefreshView,
)
from .views import (
    CustomerProfileView,
    CustomerRegistrationView,
)


urlpatterns = [
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
