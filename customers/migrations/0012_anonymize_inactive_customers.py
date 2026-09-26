import uuid

from django.db import migrations


def anonymize_inactive_customers(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    Address = apps.get_model("customers", "Address")
    Favorite = apps.get_model("customers", "Favorite")
    ProductWatch = apps.get_model("customers", "ProductWatch")
    CustomerNotification = apps.get_model("customers", "CustomerNotification")
    DiscountCode = apps.get_model("products", "DiscountCode")
    db_alias = schema_editor.connection.alias
    connection = schema_editor.connection
    cart_table = connection.ops.quote_name("orders_cart")
    has_cart_table = "orders_cart" in connection.introspection.table_names()

    queryset = Customer.objects.using(db_alias).filter(
        is_active=False,
        is_superuser=False,
    )

    for customer in queryset.iterator():
        Address.objects.using(db_alias).filter(customer_id=customer.pk).update(
            is_active=False,
            is_default=False,
        )
        Favorite.objects.using(db_alias).filter(customer_id=customer.pk).update(
            is_active=False,
        )
        ProductWatch.objects.using(db_alias).filter(customer_id=customer.pk).update(
            is_active=False,
        )
        if has_cart_table:
            schema_editor.execute(
                f"UPDATE {cart_table} SET is_active = %s "
                "WHERE customer_id = %s AND is_active = %s",
                [False, customer.pk, True],
            )
        DiscountCode.objects.using(db_alias).filter(
            customer_id=customer.pk,
            is_active=True,
        ).update(is_active=False)
        CustomerNotification.objects.using(db_alias).filter(
            customer_id=customer.pk,
        ).delete()

        token = uuid.uuid4().hex
        identity = f"deleted-{customer.pk}-{token}"
        Customer.objects.using(db_alias).filter(pk=customer.pk).update(
            username=identity[:150],
            email=f"{identity}@nexora.invalid"[:254],
            first_name="",
            last_name="",
            phone_number="",
            date_of_birth="",
            email_verified=False,
            is_staff=False,
            role="",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0011_alter_address_address_line_alter_address_city_and_more"),
    ]

    operations = [
        migrations.RunPython(
            anonymize_inactive_customers,
            migrations.RunPython.noop,
        ),
    ]
