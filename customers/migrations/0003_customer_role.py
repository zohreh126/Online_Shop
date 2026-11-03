from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0002_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("product_manager", "Product manager"),
                    ("supervisor", "Supervisor"),
                    ("operator", "Operator"),
                ],
                default="",
                max_length=30,
            ),
        ),
    ]
