from django.core.exceptions import ValidationError
from core.models import TimeStampedModel
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

class Category(TimeStampedModel):
    name = models.CharField(
        max_length=150,
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        allow_unicode=True,
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=("parent", "name"),
                name="unique_category_name_per_parent",
            ),
        ]

    def clean(self):
        super().clean()

        if self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "A category cannot be its own parent."}
            )

        ancestor = self.parent
        visited_ids = set()

        while ancestor:
            if ancestor.pk in visited_ids:
                break

            if ancestor.pk == self.pk:
                raise ValidationError(
                    {"parent": "Circular category relationship is not allowed."}
                )

            visited_ids.add(ancestor.pk)
            ancestor = ancestor.parent

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                self.name,
                allow_unicode=True,
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name



class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def in_stock(self):
        return self.active().filter(stock_quantity__gt=0)


class Product(TimeStampedModel):
    name = models.CharField(
        max_length=200,
    )

    slug = models.SlugField(
        max_length=230,
        unique=True,
        allow_unicode=True,
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )

    brand = models.CharField(
        max_length=150,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    specifications = models.JSONField(
        default=dict,
        blank=True,
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    stock_quantity = models.PositiveIntegerField(
        default=0,
    )

    image = models.ImageField(
        upload_to="products/%Y/%m/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=("is_active",)),
            models.Index(fields=("category", "is_active")),
            models.Index(fields=("sku",)),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                self.name,
                allow_unicode=True,
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    def __str__(self):
        return f"{self.name} ({self.sku})"
