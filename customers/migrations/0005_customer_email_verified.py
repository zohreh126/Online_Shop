from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("customers", "0004_address_is_active")]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
    ]
