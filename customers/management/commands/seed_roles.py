from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from customers.models import Address, Customer
from orders.models import Order, OrderItem
from products.models import Category, Discount, DiscountCode, Product


ROLE_PERMISSIONS = {
    Customer.Role.PRODUCT_MANAGER: {
        Product: ("view", "add", "change", "delete"),
        Category: ("view", "add", "change", "delete"),
        Discount: ("view", "add", "change", "delete"),
        DiscountCode: ("view", "add", "change", "delete"),
    },
    Customer.Role.SUPERVISOR: {
        Customer: ("view",),
        Address: ("view",),
        Category: ("view",),
        Product: ("view",),
        Discount: ("view",),
        DiscountCode: ("view",),
        Order: ("view",),
        OrderItem: ("view",),
    },
    Customer.Role.OPERATOR: {
        Customer: ("view", "change"),
        Address: ("view", "add", "change", "delete"),
        Order: ("view", "change"),
        OrderItem: ("view", "change"),
    },
}


class Command(BaseCommand):
    help = "Create Nexora staff groups and synchronize their permissions."

    @transaction.atomic
    def handle(self, *args, **options):
        role_groups = {}

        for role, model_permissions in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            permissions = []

            for model, actions in model_permissions.items():
                content_type = ContentType.objects.get_for_model(model)
                permissions.extend(
                    Permission.objects.filter(
                        content_type=content_type,
                        codename__in=[
                            f"{action}_{model._meta.model_name}"
                            for action in actions
                        ],
                    )
                )

            group.permissions.set(permissions)
            role_groups[role] = group

        for customer in Customer.objects.exclude(role=""):
            customer.groups.remove(*role_groups.values())
            customer.groups.add(role_groups[customer.role])

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {len(role_groups)} Nexora roles and "
                f"{Customer.objects.exclude(role='').count()} staff users."
            )
        )
