import django_filters
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import filters as drf_filters
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product, ProductReview
from .serializers import CategorySerializer, ProductReviewSerializer, ProductSerializer


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
            .prefetch_related("children")
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
    has_discount = django_filters.BooleanFilter(method="filter_has_discount")
    min_stock = django_filters.NumberFilter(
        field_name="stock_quantity",
        lookup_expr="gte",
    )
    max_stock = django_filters.NumberFilter(
        field_name="stock_quantity",
        lookup_expr="lte",
    )

    class Meta:
        model = Product
        fields = (
            "category",
            "brand",
            "min_price",
            "max_price",
            "in_stock",
            "has_discount",
            "min_stock",
            "max_stock",
        )

    def filter_in_stock(self, queryset, name, value):
        if value is None:
            return queryset

        if value:
            return queryset.filter(stock_quantity__gt=0)

        return queryset.filter(stock_quantity=0)

    def filter_has_discount(self, queryset, name, value):
        if value is None:
            return queryset

        now = timezone.now()
        active_discount = (
            Q(discount__is_active=True)
            & (Q(discount__starts_at__isnull=True) | Q(discount__starts_at__lte=now))
            & (Q(discount__ends_at__isnull=True) | Q(discount__ends_at__gte=now))
        )

        if value:
            return queryset.filter(active_discount)

        return queryset.filter(~active_discount)


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
            .annotate(
                rating_average_value=Avg(
                    "reviews__rating",
                    filter=Q(reviews__is_active=True, reviews__is_approved=True),
                ),
                rating_count_value=Count(
                    "reviews",
                    filter=Q(reviews__is_active=True, reviews__is_approved=True),
                ),
            )
            .order_by("-created_at")
        )

    @action(detail=True, methods=("get", "post"), url_path="reviews")
    def reviews(self, request, slug=None):
        product = self.get_object()
        if request.method == "GET":
            reviews = ProductReview.objects.filter(
                product=product,
                is_active=True,
                is_approved=True,
            ).select_related("customer").order_by("-created_at")
            data = ProductReviewSerializer(
                reviews,
                many=True,
                context={"request": request},
            ).data
            ratings = list(reviews.values_list("rating", flat=True))
            average = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
            return Response({"results": data, "count": len(ratings), "average": average})

        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication is required to write a review."},
                status=401,
            )

        review = ProductReview.objects.filter(
            product=product,
            customer=request.user,
        ).first()
        if review and not review.is_active:
            review.is_active = True
        serializer = ProductReviewSerializer(
            review,
            data=request.data,
            partial=review is not None,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        saved_review = serializer.save(
            product=product,
            customer=request.user,
            is_active=True,
            is_approved=True,
        )
        visible_ratings = list(
            ProductReview.objects.filter(
                product=product,
                is_active=True,
                is_approved=True,
            ).values_list("rating", flat=True)
        )
        average = round(sum(visible_ratings) / len(visible_ratings), 1) if visible_ratings else 0.0
        return Response(
            {
                "review": ProductReviewSerializer(
                    saved_review,
                    context={"request": request},
                ).data,
                "count": len(visible_ratings),
                "average": average,
            },
            status=200 if review else 201,
        )
