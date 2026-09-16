"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from core.health import health_check

import customers.schema  # noqa: F401

urlpatterns = [
    path("", TemplateView.as_view(template_name="storefront/index.html"), name="storefront-home"),
    path("about/", TemplateView.as_view(template_name="storefront/about.html"), name="storefront-about"),
    path("contact/", TemplateView.as_view(template_name="storefront/contact.html"), name="storefront-contact"),
    path("products/<slug:slug>/", TemplateView.as_view(template_name="storefront/product-detail.html"), name="storefront-product-detail"),
    path("checkout/", TemplateView.as_view(template_name="storefront/checkout.html"), name="storefront-checkout"),
    path("order-result/", TemplateView.as_view(template_name="storefront/order-result.html"), name="storefront-order-result"),
    path("account/", TemplateView.as_view(template_name="storefront/account.html"), name="storefront-account"),
    path("dashboard/", TemplateView.as_view(template_name="storefront/dashboard.html"), name="storefront-dashboard"),
    path("profile/", TemplateView.as_view(template_name="storefront/profile.html"), name="storefront-profile"),
    path('admin/', admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/v1/", include("products.urls")),
    path("api/v1/auth/", include("customers.urls")),
    path("api/v1/cart/", include("orders.urls")),
    path("api/v1/orders/", include("orders.order_urls")),
    path("api/v1/admin/orders/", include("orders.admin_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
