from rest_framework.routers import DefaultRouter

from .views import AdminOrderViewSet


router = DefaultRouter()
router.register("", AdminOrderViewSet, basename="admin-order")

urlpatterns = router.urls
