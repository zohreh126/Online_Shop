from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartDetailView, CartItemViewSet, CheckoutView


router = DefaultRouter()
router.register("items", CartItemViewSet, basename="cart-item")

urlpatterns = [
    path("", CartDetailView.as_view(), name="cart-detail"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("", include(router.urls)),
]
