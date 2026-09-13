class RolePermissionAdminMixin:
    """Make Django Admin permissions follow Django's assigned permissions."""

    def _has_model_permission(self, request, action):
        if request.user.is_superuser:
            return True

        opts = self.model._meta
        return request.user.has_perm(
            f"{opts.app_label}.{action}_{opts.model_name}"
        )

    def has_module_permission(self, request):
        return any(
            self._has_model_permission(request, action)
            for action in ("view", "add", "change", "delete")
        )

    def has_view_permission(self, request, obj=None):
        return self._has_model_permission(request, "view")

    def has_add_permission(self, request):
        return self._has_model_permission(request, "add")

    def has_change_permission(self, request, obj=None):
        return self._has_model_permission(request, "change")

    def has_delete_permission(self, request, obj=None):
        return self._has_model_permission(request, "delete")

    def delete_model(self, request, obj):
        if hasattr(obj, "is_active"):
            obj.is_active = False
            obj.save(update_fields=("is_active",))
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        if hasattr(self.model, "is_active"):
            queryset.update(is_active=False)
            return
        super().delete_queryset(request, queryset)
