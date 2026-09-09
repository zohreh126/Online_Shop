import django_filters
from rest_framework import filters as drf_filters
from rest_framework import permissions, viewsets

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryFilter(django_filters.FilterSet):
    parent = django_filters.CharFilter(
        field_name="parent__slug",
        lookup_expr="iexact",
    )
    root = django_filters.BooleanFilter(method="filter_root")

    class Meta:
        model = Category
        fields = ("parent", "root")

    def filter_root(self, queryset, name, value):
        if value is None:
            return queryset

        if value:
            return queryset.filter(parent__isnull=True)

        return queryset.filter(parent__isnull=False)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    )
    filterset_class = CategoryFilter
    search_fields = ("name", "slug")
    ordering_fields = ("name", "created_at")
    ordering = ("name",)

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .select_related("parent")
            .order_by("name")
        )


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__slug",
        lookup_expr="iexact",
    )
    brand = django_filters.CharFilter(
        field_name="brand",
        lookup_expr="icontains",
    )
    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
    )
    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
    )
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = (
            "category",
            "brand",
            "min_price",
            "max_price",
            "in_stock",
        )

    def filter_in_stock(self, queryset, name, value):
        if value is None:
            return queryset

        if value:
            return queryset.filter(stock_quantity__gt=0)

        return queryset.filter(stock_quantity=0)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    )
    filterset_class = ProductFilter
    search_fields = (
        "name",
        "brand",
        "description",
        "sku",
        "category__name",
    )
    ordering_fields = (
        "name",
        "price",
        "created_at",
        "stock_quantity",
    )
    ordering = ("-created_at",)

    def get_queryset(self):
        return (
            Product.objects.active()
            .select_related("category", "discount")
            .order_by("-created_at")
        )
