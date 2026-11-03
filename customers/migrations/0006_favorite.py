from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0005_customer_email_verified"),
        ("products", "0004_discountcode"),
    ]

    operations = [
        migrations.CreateModel(
            name="Favorite",
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
                ("is_active", models.BooleanField(default=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favorites",
                        to="customers.customer",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="favorites",
                        to="products.product",
                    ),
                ),
            ],
            options={
                "verbose_name": "Favorite",
                "verbose_name_plural": "Favorites",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(
                        fields=["customer", "is_active"],
                        name="favorite_customer_active_idx",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="favorite",
            constraint=models.UniqueConstraint(
                fields=("customer", "product"),
                name="unique_customer_favorite",
            ),
        ),
    ]
