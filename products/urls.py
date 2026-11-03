from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ActiveCampaignView, CategoryViewSet, ProductViewSet


router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("campaigns/active/", ActiveCampaignView.as_view(), name="active-campaign"),
] + router.urls
