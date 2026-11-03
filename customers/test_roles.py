from io import StringIO

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase

from customers.management.commands.seed_roles import PROJECT_MODELS

from .models import Customer


class NexoraRolesTests(TestCase):
    def test_seed_roles_creates_groups_and_permissions(self):
        call_command("seed_roles", stdout=StringIO())

        product_manager = Group.objects.get(name=Customer.Role.PRODUCT_MANAGER)
        supervisor = Group.objects.get(name=Customer.Role.SUPERVISOR)
        operator = Group.objects.get(name=Customer.Role.OPERATOR)

        self.assertTrue(
            product_manager.permissions.filter(
                codename="change_product"
            ).exists()
        )
        self.assertTrue(
            supervisor.permissions.filter(
                codename="view_order"
            ).exists()
        )
        self.assertTrue(
            operator.permissions.filter(
                codename="change_address"
            ).exists()
        )
        self.assertTrue(
            supervisor.permissions.filter(
                codename="view_productreview"
            ).exists()
        )
        self.assertFalse(
            operator.permissions.filter(
                codename="view_productreview"
            ).exists()
        )
        self.assertTrue(
            supervisor.permissions.filter(
                codename="view_sitefeedback"
            ).exists()
        )

    def permission_exists(self, group, model, action):
        content_type = ContentType.objects.get_for_model(model)
        return group.permissions.filter(
            content_type=content_type,
            codename=f"{action}_{model._meta.model_name}",
        ).exists()

    def test_supervisor_can_view_every_project_model_read_only(self):
        call_command("seed_roles", stdout=StringIO())
        supervisor = Group.objects.get(name=Customer.Role.SUPERVISOR)

        for model in PROJECT_MODELS:
            self.assertTrue(
                self.permission_exists(supervisor, model, "view"),
                f"Supervisor is missing view permission for {model.__name__}",
            )
            for action in ("add", "change", "delete"):
                self.assertFalse(
                    self.permission_exists(supervisor, model, action),
                    f"Supervisor unexpectedly has {action} permission for {model.__name__}",
                )

    def test_product_manager_can_manage_catalog_discount_models_only(self):
        call_command("seed_roles", stdout=StringIO())
        product_manager = Group.objects.get(name=Customer.Role.PRODUCT_MANAGER)

        for model_name in ("Product", "Category", "Discount", "DiscountCode"):
            model = next(model for model in PROJECT_MODELS if model.__name__ == model_name)
            for action in ("view", "add", "change", "delete"):
                self.assertTrue(self.permission_exists(product_manager, model, action))

        order_model = next(model for model in PROJECT_MODELS if model.__name__ == "Order")
        self.assertFalse(self.permission_exists(product_manager, order_model, "view"))

    def test_operator_can_manage_customers_addresses_and_orders(self):
        call_command("seed_roles", stdout=StringIO())
        operator = Group.objects.get(name=Customer.Role.OPERATOR)

        for model_name in ("Customer", "Address", "Order"):
            model = next(model for model in PROJECT_MODELS if model.__name__ == model_name)
            for action in ("view", "add", "change", "delete"):
                self.assertTrue(self.permission_exists(operator, model, action))

        order_item = next(model for model in PROJECT_MODELS if model.__name__ == "OrderItem")
        self.assertTrue(self.permission_exists(operator, order_item, "view"))
        self.assertTrue(self.permission_exists(operator, order_item, "change"))

        product = next(model for model in PROJECT_MODELS if model.__name__ == "Product")
        self.assertFalse(self.permission_exists(operator, product, "view"))

    def test_seed_roles_syncs_customer_role_to_group(self):
        customer = Customer.objects.create_user(
            username="roleuser",
            email="role@example.com",
            password="SecurePass#2026",
            role=Customer.Role.PRODUCT_MANAGER,
        )

        call_command("seed_roles", stdout=StringIO())

        self.assertTrue(
            customer.groups.filter(
                name=Customer.Role.PRODUCT_MANAGER
            ).exists()
        )

    def test_customer_role_is_optional_for_regular_customers(self):
        customer = Customer.objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password="SecurePass#2026",
        )

        self.assertEqual(customer.role, "")

    def test_seed_roles_promotes_and_demotes_non_superusers(self):
        customer = Customer.objects.create_user(
            username="staff-sync-user",
            email="staff-sync@example.com",
            password="SecurePass#2026",
            role=Customer.Role.OPERATOR,
        )

        call_command("seed_roles", stdout=StringIO())
        customer.refresh_from_db()
        self.assertTrue(customer.is_staff)

        customer.role = ""
        customer.save(update_fields=("role",))
        call_command("seed_roles", stdout=StringIO())
        customer.refresh_from_db()

        self.assertFalse(customer.is_staff)
        self.assertFalse(customer.groups.exists())
