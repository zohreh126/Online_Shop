from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from customers.models import (
    Address,
    Customer,
    CustomerNotification,
    Favorite,
    ProductWatch,
    SiteFeedback,
)
from orders.models import Cart, CartItem, Order, OrderItem, RewardTransaction
from products.models import (
    Category,
    Discount,
    DiscountCode,
    Product,
    ProductQuestion,
    ProductReview,
    ProductReviewHelpfulVote,
)

# These are the application's own admin-managed models.  Keeping the list in
# one place makes the supervisor role auditable: a supervisor can inspect every
# business section without accidentally receiving write access.
PROJECT_MODELS = (
    Customer,
    Address,
    Favorite,
    ProductWatch,
    SiteFeedback,
    CustomerNotification,
    Category,
    Product,
    ProductReview,
    ProductReviewHelpfulVote,
    ProductQuestion,
    Discount,
    DiscountCode,
    Cart,
    CartItem,
    Order,
    OrderItem,
    RewardTransaction,
)


ROLE_PERMISSIONS = {
    Customer.Role.PRODUCT_MANAGER: {
        Product: ("view", "add", "change", "delete"),
        Category: ("view", "add", "change", "delete"),
        Discount: ("view", "add", "change", "delete"),
        DiscountCode: ("view", "add", "change", "delete"),
        ProductReview: ("view", "change"),
        ProductQuestion: ("view", "change"),
        SiteFeedback: ("view",),
    },
    # The PDF defines the supervisor as a read-only observer of all sections
    # of the admin panel.  The explicit map is generated from the complete
    # project model list so newly registered business models cannot be missed.
    Customer.Role.SUPERVISOR: {
        model: ("view",)
        for model in PROJECT_MODELS
    },
    Customer.Role.OPERATOR: {
        Customer: ("view", "add", "change", "delete"),
        Address: ("view", "add", "change", "delete"),
        Order: ("view", "add", "change", "delete"),
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

        for customer in Customer.objects.all():
            customer.groups.remove(*role_groups.values())
            if customer.role in role_groups:
                customer.groups.add(role_groups[customer.role])
                if not customer.is_staff:
                    customer.is_staff = True
                    customer.save(update_fields=("is_staff",))
            elif customer.is_staff and not customer.is_superuser:
                customer.is_staff = False
                customer.save(update_fields=("is_staff",))

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {len(role_groups)} Nexora roles and "
                f"{Customer.objects.filter(role__in=role_groups).count()} staff users."
            )
        )
