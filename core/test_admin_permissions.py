from io import StringIO

from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.test.client import RequestFactory

from customers.models import Address, Customer
from orders.models import Order
from products.models import Product


class AdminPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles", stdout=StringIO())

        cls.product_manager = Customer.objects.create_user(
            username="admin-product-manager",
            email="admin-product-manager@example.com",
            password="SecurePass#2026",
            role=Customer.Role.PRODUCT_MANAGER,
            is_staff=True,
        )
        cls.supervisor = Customer.objects.create_user(
            username="admin-supervisor",
            email="admin-supervisor@example.com",
            password="SecurePass#2026",
            role=Customer.Role.SUPERVISOR,
            is_staff=True,
        )
        cls.operator = Customer.objects.create_user(
            username="admin-operator",
            email="admin-operator@example.com",
            password="SecurePass#2026",
            role=Customer.Role.OPERATOR,
            is_staff=True,
        )
        cls.superuser = Customer.objects.create_superuser(
            username="admin-superuser",
            email="admin-superuser@example.com",
            password="SecurePass#2026",
        )
        call_command("seed_roles", stdout=StringIO())

    def admin_for(self, model):
        return admin.site._registry[model]

    def request_for(self, user):
        request = RequestFactory().get("/admin/")
        request.user = user
        return request

    def test_product_manager_can_manage_catalog_but_not_orders(self):
        product_admin = self.admin_for(Product)
        order_admin = self.admin_for(Order)
        request = self.request_for(self.product_manager)

        self.assertTrue(product_admin.has_change_permission(request))
        self.assertTrue(product_admin.has_delete_permission(request))
        self.assertFalse(order_admin.has_view_permission(request))

    def test_supervisor_can_view_but_not_change_products(self):
        product_admin = self.admin_for(Product)
        request = self.request_for(self.supervisor)

        self.assertTrue(product_admin.has_view_permission(request))
        self.assertFalse(product_admin.has_change_permission(request))

    def test_operator_can_manage_customers_addresses_and_orders(self):
        customer_admin = self.admin_for(Customer)
        address_admin = self.admin_for(Address)
        order_admin = self.admin_for(Order)
        product_admin = self.admin_for(Product)
        request = self.request_for(self.operator)

        self.assertTrue(customer_admin.has_change_permission(request))
        self.assertTrue(address_admin.has_add_permission(request))
        self.assertTrue(order_admin.has_change_permission(request))
        self.assertFalse(product_admin.has_view_permission(request))

    def test_superuser_has_full_admin_access(self):
        product_admin = self.admin_for(Product)
        order_admin = self.admin_for(Order)
        request = self.request_for(self.superuser)

        self.assertTrue(product_admin.has_delete_permission(request))
        self.assertTrue(order_admin.has_change_permission(request))

    def test_customer_admin_syncs_role_group_when_saved(self):
        customer_admin = self.admin_for(Customer)
        request = self.request_for(self.superuser)

        self.product_manager.role = Customer.Role.OPERATOR
        customer_admin.save_model(request, self.product_manager, form=None, change=True)

        self.assertTrue(
            self.product_manager.groups.filter(
                name=Customer.Role.OPERATOR,
            ).exists()
        )
        self.assertFalse(
            self.product_manager.groups.filter(
                name=Customer.Role.PRODUCT_MANAGER,
            ).exists()
        )
