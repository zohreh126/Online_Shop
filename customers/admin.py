from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.admin_permissions import RolePermissionAdminMixin

from .management.commands.seed_roles import ROLE_PERMISSIONS
from .models import Address, Customer


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm("customers.add_address")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("customers.change_address")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("customers.delete_address")


@admin.register(Customer)
class CustomerAdmin(RolePermissionAdminMixin, BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "role_badge",
    )

    list_filter = (
        "is_staff",
        "is_active",
        "is_superuser",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
    )

    ordering = ("username",)

    inlines = [AddressInline]

    fieldsets = (
        (None, {
            "fields": (
                "username",
                "password",
            ),
        }),
        ("Personal information", {
            "fields": (
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "role",
            ),
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        ("Important dates", {
            "fields": (
                "last_login",
                "date_joined",
            ),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "password1",
                "password2",
                "is_staff",
                "is_active",
                "role",
            ),
        }),
    )

    readonly_fields = (
        "last_login",
        "date_joined",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields.extend(
                ("role", "is_staff", "is_superuser", "groups", "user_permissions")
            )
        return tuple(dict.fromkeys(readonly_fields))

    @admin.display(description="Role", ordering="role")
    def role_badge(self, obj):
        labels = {
            Customer.Role.PRODUCT_MANAGER: ("Product manager", "#7150b4"),
            Customer.Role.SUPERVISOR: ("Supervisor", "#39739d"),
            Customer.Role.OPERATOR: ("Operator", "#4d8a5c"),
        }
        label, color = labels.get(obj.role, ("Customer", "#77727f"))
        return format_html(
            '<span style="color:{};font-weight:700">● {}</span>',
            color,
            label,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        role_groups = Group.objects.filter(name__in=ROLE_PERMISSIONS)
        obj.groups.remove(*role_groups)
        if obj.role in ROLE_PERMISSIONS:
            group, _ = Group.objects.get_or_create(name=obj.role)
            obj.groups.add(group)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets

        return tuple(
            (
                title,
                {
                    **options,
                    "fields": tuple(
                        field
                        for field in options["fields"]
                        if field not in {
                            "is_staff",
                            "is_superuser",
                            "groups",
                            "user_permissions",
                        }
                    ),
                },
            )
            for title, options in fieldsets
        )


@admin.register(Address)
class AddressAdmin(RolePermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "customer",
        "title",
        "province",
        "city",
        "is_default",
    )

    list_filter = (
        "province",
        "city",
        "is_default",
    )

    search_fields = (
        "customer__username",
        "customer__email",
        "recipient_name",
        "postal_code",
    )

    autocomplete_fields = ("customer",)
