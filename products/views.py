from collections import Counter

import django_filters
from django.db.models import Avg, Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import filters as drf_filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem

from .models import (
    Category,
    DiscountCode,
    Product,
    ProductQuestion,
    ProductReview,
    ProductReviewHelpfulVote,
)
from .serializers import (
    CategorySerializer,
    ProductQuestionAnswerSerializer,
    ProductQuestionSerializer,
    ProductReviewSerializer,
    ProductSerializer,
)


class ActiveCampaignView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        campaign = (
            DiscountCode.objects.filter(customer__isnull=True, is_active=True)
            .order_by("-created_at")
            .first()
        )
        if campaign is None or not campaign.is_valid_now:
            return Response({"campaign": None}, status=status.HTTP_200_OK)
        return Response(
            {
                "campaign": {
                    "code": campaign.code,
                    "discount_type": campaign.discount_type,
                    "value": campaign.value,
                    "minimum_order_amount": campaign.minimum_order_amount,
                    "ends_at": campaign.ends_at,
                }
            },
            status=status.HTTP_200_OK,
        )


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

    @staticmethod
    def review_statistics(reviews):
        ratings = list(reviews.values_list("rating", flat=True))
        counts = Counter(ratings)
        return {
            "count": len(ratings),
            "average": round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
            "rating_distribution": {
                str(rating): counts.get(rating, 0)
                for rating in range(5, 0, -1)
            },
        }

    @action(detail=True, methods=("get", "post"), url_path="reviews")
    def reviews(self, request, slug=None):
        product = self.get_object()
        if request.method == "GET":
            reviews = ProductReview.objects.filter(
                product=product,
                is_active=True,
                is_approved=True,
            ).select_related("customer").annotate(
                helpful_count_value=Count("helpful_votes", distinct=True),
                verified_purchase_value=Exists(
                    OrderItem.objects.filter(
                        product_id=OuterRef("product_id"),
                        order__customer_id=OuterRef("customer_id"),
                        order__payment_status=Order.PaymentStatus.PAID,
                    )
                ),
            )
            review_sort = request.query_params.get("sort", "newest").strip().lower()
            review_ordering = {
                "highest": ("-rating", "-created_at"),
                "helpful": ("-helpful_count_value", "-rating", "-created_at"),
            }.get(review_sort, ("-created_at",))
            reviews = reviews.order_by(*review_ordering)
            if request.user.is_authenticated:
                reviews = reviews.annotate(
                    helpful_by_me_value=Exists(
                        ProductReviewHelpfulVote.objects.filter(
                            review=OuterRef("pk"),
                            customer=request.user,
                        )
                    )
                )
            data = ProductReviewSerializer(
                reviews,
                many=True,
                context={"request": request},
            ).data
            return Response(
                {
                    "results": data,
                    **self.review_statistics(reviews),
                }
            )

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
        visible_reviews = ProductReview.objects.filter(
            product=product,
            is_active=True,
            is_approved=True,
        )
        statistics = self.review_statistics(visible_reviews)
        return Response(
            {
                "review": ProductReviewSerializer(
                    saved_review,
                    context={"request": request},
                ).data,
                **statistics,
            },
            status=200 if review else 201,
        )

    @action(detail=True, methods=("get", "post"), url_path="questions")
    def questions(self, request, slug=None):
        product = self.get_object()
        visible_questions = ProductQuestion.objects.filter(
            product=product,
            is_active=True,
            is_approved=True,
        ).select_related("customer").order_by("-created_at")

        if request.method == "GET":
            return Response(
                {
                    "results": ProductQuestionSerializer(
                        visible_questions,
                        many=True,
                        context={"request": request},
                    ).data,
                    "count": visible_questions.count(),
                }
            )

        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication is required to ask a question."},
                status=401,
            )

        serializer = ProductQuestionSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        question = serializer.save(
            product=product,
            customer=request.user,
            is_active=True,
            is_approved=True,
        )
        return Response(
            {
                "question": ProductQuestionSerializer(
                    question,
                    context={"request": request},
                ).data,
                "count": visible_questions.count(),
            },
            status=201,
        )

    @extend_schema(
        request=ProductQuestionAnswerSerializer,
        responses=ProductQuestionSerializer,
    )
    @action(
        detail=True,
        methods=("patch",),
        url_path=r"questions/(?P<question_id>[0-9]+)/answer",
        permission_classes=(permissions.IsAdminUser,),
    )
    def answer_question(self, request, slug=None, question_id=None):
        product = self.get_object()
        question = get_object_or_404(
            ProductQuestion,
            product=product,
            pk=question_id,
            is_active=True,
        )
        serializer = ProductQuestionAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question.answer = serializer.validated_data["answer"]
        question.answered_at = timezone.now()
        question.save(update_fields=("answer", "answered_at", "updated_at"))
        return Response(
            ProductQuestionSerializer(
                question,
                context={"request": request},
            ).data
        )

    @action(
        detail=True,
        methods=("post",),
        url_path=r"reviews/(?P<review_id>[0-9]+)/helpful",
    )
    def review_helpful(self, request, slug=None, review_id=None):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication is required to vote on a review."},
                status=401,
            )

        product = self.get_object()
        review = get_object_or_404(
            ProductReview,
            pk=review_id,
            product=product,
            is_active=True,
            is_approved=True,
        )
        vote = ProductReviewHelpfulVote.objects.filter(
            review=review,
            customer=request.user,
        ).first()
        if vote:
            vote.delete()
            helpful = False
        else:
            ProductReviewHelpfulVote.objects.create(
                review=review,
                customer=request.user,
            )
            helpful = True

        return Response(
            {
                "helpful": helpful,
                "helpful_count": review.helpful_votes.count(),
            }
        )
