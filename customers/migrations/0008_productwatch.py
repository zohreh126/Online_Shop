from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0007_sitefeedback"),
        ("products", "0005_product_review"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductWatch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("notify_price_drop", models.BooleanField(default=True)),
                ("notify_restock", models.BooleanField(default=True)),
                (
                    "target_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Optional threshold for price-drop notifications.",
                        max_digits=12,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00"))
                        ],
                    ),
                ),
                (
                    "last_seen_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                    ),
                ),
                ("last_seen_stock_quantity", models.PositiveIntegerField(default=0)),
                ("last_price_notified_at", models.DateTimeField(blank=True, null=True)),
                ("last_restock_notified_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_watches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="product_watches",
                        to="products.product",
                    ),
                ),
            ],
            options={
                "verbose_name": "Product watch",
                "verbose_name_plural": "Product watches",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(
                        fields=["customer", "is_active"],
                        name="watch_customer_active_idx",
                    ),
                    models.Index(
                        fields=["product", "is_active"],
                        name="watch_product_active_idx",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="productwatch",
            constraint=models.UniqueConstraint(
                fields=("customer", "product"),
                name="unique_customer_product_watch",
            ),
        ),
    ]
