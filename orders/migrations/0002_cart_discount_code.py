from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
        ("products", "0004_discountcode"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="discount_code",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="carts",
                to="products.discountcode",
            ),
        ),
    ]
