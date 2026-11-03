from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0003_customer_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="address",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
