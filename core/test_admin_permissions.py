from io import StringIO

from django.contrib import admin
from django.core.management import call_command
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from customers.management.commands.seed_roles import PROJECT_MODELS
from customers.models import Address, Customer
from orders.models import Cart, CartItem, Order
from products.models import (
    Product,
    ProductQuestion,
    ProductReviewHelpfulVote,
)


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
        question_admin = self.admin_for(ProductQuestion)
        order_admin = self.admin_for(Order)
        request = self.request_for(self.product_manager)

        self.assertTrue(product_admin.has_change_permission(request))
        self.assertTrue(product_admin.has_delete_permission(request))
        self.assertTrue(question_admin.has_view_permission(request))
        self.assertTrue(question_admin.has_change_permission(request))
        self.assertFalse(order_admin.has_view_permission(request))

    def test_supervisor_can_view_but_not_change_products(self):
        product_admin = self.admin_for(Product)
        question_admin = self.admin_for(ProductQuestion)
        request = self.request_for(self.supervisor)

        self.assertTrue(product_admin.has_view_permission(request))
        self.assertFalse(product_admin.has_change_permission(request))
        self.assertTrue(question_admin.has_view_permission(request))
        self.assertFalse(question_admin.has_change_permission(request))
        self.assertFalse(question_admin.has_delete_permission(request))

    def test_operator_can_manage_customers_addresses_and_orders(self):
        customer_admin = self.admin_for(Customer)
        address_admin = self.admin_for(Address)
        order_admin = self.admin_for(Order)
        product_admin = self.admin_for(Product)
        question_admin = self.admin_for(ProductQuestion)
        request = self.request_for(self.operator)

        self.assertTrue(customer_admin.has_change_permission(request))
        self.assertTrue(customer_admin.has_add_permission(request))
        self.assertTrue(customer_admin.has_delete_permission(request))
        self.assertTrue(address_admin.has_add_permission(request))
        self.assertTrue(order_admin.has_change_permission(request))
        self.assertTrue(order_admin.has_add_permission(request))
        self.assertTrue(order_admin.has_delete_permission(request))
        self.assertFalse(product_admin.has_view_permission(request))
        self.assertFalse(question_admin.has_view_permission(request))
        self.assertFalse(question_admin.has_change_permission(request))

    def test_every_project_model_has_a_custom_admin(self):
        for model in PROJECT_MODELS:
            self.assertIn(
                model,
                admin.site._registry,
                f"{model.__name__} is missing from the custom admin panel",
            )

    def test_supervisor_can_view_new_cart_and_feedback_models_read_only(self):
        request = self.request_for(self.supervisor)
        for model in (Cart, CartItem, ProductReviewHelpfulVote):
            model_admin = self.admin_for(model)
            self.assertTrue(model_admin.has_view_permission(request))
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))

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
        self.assertTrue(self.product_manager.is_staff)

        self.product_manager.role = ""
        customer_admin.save_model(request, self.product_manager, form=None, change=True)
        self.product_manager.refresh_from_db()
        self.assertFalse(self.product_manager.is_staff)

    def test_root_administrator_is_not_listed_as_a_customer(self):
        customer_admin = self.admin_for(Customer)
        request = self.request_for(self.superuser)

        queryset = customer_admin.get_queryset(request)

        self.assertNotIn(self.superuser.pk, queryset.values_list("pk", flat=True))

    def test_staff_accounts_are_not_listed_as_storefront_customers(self):
        customer_admin = self.admin_for(Customer)
        request = self.request_for(self.superuser)

        queryset = customer_admin.get_queryset(request)

        self.assertNotIn(self.product_manager.pk, queryset.values_list("pk", flat=True))
        self.assertNotIn(self.supervisor.pk, queryset.values_list("pk", flat=True))
        self.assertNotIn(self.operator.pk, queryset.values_list("pk", flat=True))

    def test_inactive_customers_are_not_listed_in_customer_admin(self):
        archived = Customer.objects.create_user(
            username="archived-shopper",
            email="archived-shopper@example.com",
            password="SecurePass#2026",
        )
        archived.delete()

        customer_admin = self.admin_for(Customer)
        request = self.request_for(self.superuser)
        queryset = customer_admin.get_queryset(request)

        self.assertNotIn(archived.pk, queryset.values_list("pk", flat=True))

    def test_admin_dashboard_uses_nexora_control_center(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nexora-admin-hero")
        self.assertContains(response, "مرکز فرماندهی فروشگاه")
        self.assertContains(response, "مشاهده فروشگاه")
        self.assertContains(response, "مدیر کل")
        self.assertContains(response, "nexora-admin-role-pill")
        self.assertContains(response, "نظرات کاربران")
        self.assertContains(response, "nexora-kpi-grid")
        self.assertContains(response, "nexora-quick-actions")
        self.assertContains(response, "عملیات سریع")
        self.assertContains(response, "آخرین سفارش‌ها")
        self.assertContains(response, "آخرین نظرها")
        self.assertContains(response, "پرسش‌های محصول")
        self.assertContains(response, "پرسش‌های بی‌پاسخ")
        self.assertContains(response, "آخرین پرسش‌ها")
        self.assertContains(response, "موجودی رو به اتمام")
        self.assertContains(response, "تخفیف‌های رو به پایان")
        self.assertContains(response, "نبض تجربه‌ی مشتری")
        self.assertContains(response, "nexora-ops-grid")
        self.assertContains(response, "/static/admin/css/nexora-admin.css")
        self.assertContains(response, "/static/admin/js/nexora-admin.js")
        self.assertContains(response, "data-admin-theme-toggle")

    def test_admin_dashboard_uses_readable_bilingual_app_cards(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nexora-app-directory")
        self.assertContains(response, "nexora-app-card")
        self.assertContains(response, "nexora-app-action-add")
        self.assertContains(response, "nexora-app-action-change")
        self.assertContains(response, "اضافه کردن")
        self.assertContains(response, "تغییر")
        self.assertContains(response, "محصولات")

    def test_admin_dashboard_switches_between_persian_and_english(self):
        self.client.force_login(self.superuser)

        english_response = self.client.post(
            reverse("set_language"),
            {
                "language": "en",
                "next": reverse("admin:index"),
            },
            follow=True,
        )

        self.assertEqual(english_response.status_code, 200)
        self.assertContains(english_response, "Store control center")
        self.assertContains(english_response, "Quick operations")
        self.assertContains(english_response, 'lang="en"')
        self.assertContains(english_response, 'dir="ltr"')
        self.assertContains(english_response, 'value="en"')
        self.assertContains(english_response, "is-active")
        self.assertNotContains(english_response, "مرکز فرماندهی فروشگاه")

        persian_response = self.client.post(
            reverse("set_language"),
            {
                "language": "fa",
                "next": reverse("admin:index"),
            },
            follow=True,
        )

        self.assertEqual(persian_response.status_code, 200)
        self.assertContains(persian_response, "مرکز فرماندهی فروشگاه")
        self.assertContains(persian_response, "عملیات سریع")
        self.assertContains(persian_response, "نظرات محصولات")
        self.assertContains(persian_response, 'lang="fa"')
        self.assertContains(persian_response, 'dir="rtl"')
        self.assertContains(persian_response, 'value="fa"')
        self.assertContains(persian_response, "is-active")

    def test_admin_inner_pages_use_persian_model_labels_and_choices(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("admin:customers_sitefeedback_changelist")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "بازخورد سایت")
        self.assertContains(response, "امتیاز")
        self.assertContains(response, "نظر")
        self.assertContains(response, "عالی")
        self.assertContains(response, "خیلی بد")
        for label in (
            "مشتری‌ها",
            "محصولات",
            "دسته‌بندی‌ها",
            "سفارش‌ها",
            "آیتم‌های سفارش",
            "تخفیف‌ها",
            "فهرست سیاه توکن",
        ):
            self.assertContains(response, label)
        self.assertNotContains(response, "Site feedback")
        self.assertNotContains(response, "Excellent")
        self.assertNotContains(response, "Very bad")
        self.assertContains(response, "Vazirmatn")
        self.assertContains(response, "fonts.googleapis.com/css2?family=Vazirmatn")

    def test_admin_header_has_one_ordered_control_bar_in_both_languages(self):
        self.client.force_login(self.superuser)

        persian_response = self.client.get(reverse("admin:index"))
        self.assertContains(persian_response, "nexora-admin-user-tools")
        self.assertContains(persian_response, "nexora-admin-links")
        self.assertContains(persian_response, "nexora-admin-controls")
        self.assertContains(persian_response, "data-theme-icon")
        self.assertContains(persian_response, 'value="fa"')
        self.assertContains(persian_response, 'value="en"')
        self.assertContains(persian_response, "Vazirmatn")
        self.assertEqual(
            persian_response.content.decode().count("data-admin-theme-toggle"),
            1,
        )
        self.assertNotContains(persian_response, 'class="theme-toggle"')

        english_response = self.client.post(
            reverse("set_language"),
            {
                "language": "en",
                "next": reverse("admin:customers_sitefeedback_changelist"),
            },
            follow=True,
        )
        self.assertContains(english_response, "Site feedback")
        self.assertContains(english_response, "Excellent")
        self.assertContains(english_response, "View site")
        self.assertContains(english_response, "Change password")
        self.assertContains(english_response, "Log out")
        self.assertEqual(
            english_response.content.decode().count("data-admin-theme-toggle"),
            1,
        )

    def test_customer_admin_delete_action_deactivates_account(self):
        customer_admin = self.admin_for(Customer)
        request = self.request_for(self.superuser)

        customer_admin.delete_queryset(
            request,
            Customer.objects.filter(pk=self.product_manager.pk),
        )
        self.product_manager.refresh_from_db()

        self.assertFalse(self.product_manager.is_active)
        self.assertFalse(self.product_manager.is_staff)
        self.assertEqual(self.product_manager.role, "")

    def test_customer_admin_single_delete_action_deactivates_account(self):
        customer_admin = self.admin_for(Customer)
        request = self.request_for(self.superuser)

        customer_admin.delete_model(request, self.product_manager)
        self.product_manager.refresh_from_db()

        self.assertFalse(self.product_manager.is_active)
        self.assertFalse(self.product_manager.is_staff)
        self.assertEqual(self.product_manager.role, "")
