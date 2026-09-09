from decimal import Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Discount, Product


class CategorySerializer(serializers.ModelSerializer):
    parent_slug = serializers.CharField(
        source="parent.slug",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "parent",
            "parent_slug",
        )
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    discount_amount = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

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
            "final_price",
            "stock_quantity",
            "is_in_stock",
            "image",
            "image_url",
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
