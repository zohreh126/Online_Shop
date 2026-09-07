from django.urls import path

from .views import (
    CustomerProfileView,
    CustomerRegistrationView,
)


urlpatterns = [
    path(
        "register/",
        CustomerRegistrationView.as_view(),
        name="customer-register",
    ),
    path(
        "profile/",
        CustomerProfileView.as_view(),
        name="customer-profile",
    ),
]
