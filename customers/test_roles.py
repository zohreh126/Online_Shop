from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

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
                codename="change_productreview"
            ).exists()
        )
        self.assertTrue(
            operator.permissions.filter(
                codename="view_productreview"
            ).exists()
        )

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
