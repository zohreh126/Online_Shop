from decimal import Decimal

from django.db.models import Avg
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Discount, Product, ProductQuestion, ProductReview


class CategorySerializer(serializers.ModelSerializer):
    parent_slug = serializers.CharField(
        source="parent.slug",
        read_only=True,
        allow_null=True,
    )
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "parent",
            "parent_slug",
            "children",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, category):
        return CategorySerializer(
            category.children.filter(is_active=True).order_by("name"),
            many=True,
            context=self.context,
        ).data


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    discount_amount = serializers.SerializerMethodField()
    discount_type = serializers.SerializerMethodField()
    discount_value = serializers.SerializerMethodField()
    discount_ends_at = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    rating_average = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "category",
            "brand",
            "description",
            "specifications",
            "price",
            "discount_amount",
            "discount_type",
            "discount_value",
            "discount_ends_at",
            "final_price",
            "stock_quantity",
            "is_in_stock",
            "image",
            "image_url",
            "rating_average",
            "rating_count",
        )
        read_only_fields = fields

    @staticmethod
    def get_product_discount(product):
        try:
            discount = product.discount
        except Discount.DoesNotExist:
            return None

        if not discount.is_valid_now:
            return None

        return discount

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_discount_amount(self, product):
        discount = self.get_product_discount(product)

        if discount is None:
            return Decimal("0.00")

        return discount.calculate_discount(product.price)

    @extend_schema_field(OpenApiTypes.STR)
    def get_discount_type(self, product):
        discount = self.get_product_discount(product)
        return discount.discount_type if discount is not None else None

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_discount_value(self, product):
        discount = self.get_product_discount(product)
        return discount.value if discount is not None else None

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_discount_ends_at(self, product):
        discount = self.get_product_discount(product)
        return discount.ends_at if discount is not None else None

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_final_price(self, product):
        discount_amount = self.get_discount_amount(product)
        final_price = product.price - discount_amount

        return max(final_price, Decimal("0.00"))

    @extend_schema_field(OpenApiTypes.URI)
    def get_image_url(self, product):
        if not product.image:
            return None

        image_url = product.image.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(image_url)

        return image_url

    @extend_schema_field(OpenApiTypes.NUMBER)
    def get_rating_average(self, product):
        if hasattr(product, "rating_average_value"):
            average = product.rating_average_value
        else:
            average = product.reviews.filter(
                is_active=True,
                is_approved=True,
            ).aggregate(average=Avg("rating"))["average"]
        return round(float(average), 1) if average is not None else 0.0

    @extend_schema_field(OpenApiTypes.INT)
    def get_rating_count(self, product):
        if hasattr(product, "rating_count_value"):
            count = product.rating_count_value
        else:
            count = product.reviews.filter(
                is_active=True,
                is_approved=True,
            ).count()
        return int(count or 0)


class ProductReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    is_verified_purchase = serializers.SerializerMethodField()
    helpful_count = serializers.SerializerMethodField()
    helpful_by_me = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = (
            "id",
            "customer_name",
            "is_mine",
            "is_verified_purchase",
            "helpful_count",
            "helpful_by_me",
            "rating",
            "title",
            "body",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer_name",
            "is_mine",
            "is_verified_purchase",
            "helpful_count",
            "helpful_by_me",
            "created_at",
            "updated_at",
        )

    def get_customer_name(self, review):
        full_name = f"{review.customer.first_name} {review.customer.last_name}".strip()
        return full_name or review.customer.username

    def get_is_mine(self, review):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and review.customer_id == request.user.id)

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_verified_purchase(self, review):
        if hasattr(review, "verified_purchase_value"):
            return bool(review.verified_purchase_value)
        return review.customer.orders.filter(
            payment_status="paid",
            items__product_id=review.product_id,
        ).exists()

    def get_helpful_count(self, review):
        if hasattr(review, "helpful_count_value"):
            return int(review.helpful_count_value or 0)
        return review.helpful_votes.count()

    def get_helpful_by_me(self, review):
        if hasattr(review, "helpful_by_me_value"):
            return bool(review.helpful_by_me_value)
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and review.helpful_votes.filter(customer=request.user).exists()
        )

    def validate_title(self, value):
        return " ".join(value.strip().split())

    def validate_body(self, value):
        value = " ".join(value.strip().split())
        if not value:
            raise serializers.ValidationError("Review text cannot be empty.")
        return value


class ProductQuestionSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = ProductQuestion
        fields = (
            "id",
            "customer_name",
            "is_mine",
            "question",
            "answer",
            "answered_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer_name",
            "is_mine",
            "answer",
            "answered_at",
            "created_at",
            "updated_at",
        )

    @extend_schema_field(OpenApiTypes.STR)
    def get_customer_name(self, question):
        full_name = f"{question.customer.first_name} {question.customer.last_name}".strip()
        return full_name or question.customer.username

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_mine(self, question):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and question.customer_id == request.user.id
        )

    def validate_question(self, value):
        value = " ".join(value.strip().split())
        if not value:
            raise serializers.ValidationError("Question text cannot be empty.")
        return value


class ProductQuestionAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField(max_length=1500, allow_blank=False)

    def validate_answer(self, value):
        value = " ".join(value.strip().split())
        if not value:
            raise serializers.ValidationError("Answer text cannot be empty.")
        return value
