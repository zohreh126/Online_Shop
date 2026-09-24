from django.contrib import admin
from django.apps import apps
from django.utils.translation import gettext_lazy as _

admin.site.site_header = _("Nexora Admin")
admin.site.site_title = _("Nexora Store Management")
admin.site.index_title = _("Store management center")


# SimpleJWT registers its token blacklist models with plain English labels.
# Keep those two technical models understandable when the rest of the panel
# is displayed in Persian as well.  Lazy translations preserve the English
# labels when the operator switches the panel back to English.
_token_blacklist = apps.get_app_config("token_blacklist")
_token_blacklist.verbose_name = _("Token blacklist")
_token_blacklist.get_model("blacklistedtoken")._meta.verbose_name = _(
    "Blacklisted token"
)
_token_blacklist.get_model("blacklistedtoken")._meta.verbose_name_plural = _(
    "Blacklisted tokens"
)
_token_blacklist.get_model("outstandingtoken")._meta.verbose_name = _(
    "Outstanding token"
)
_token_blacklist.get_model("outstandingtoken")._meta.verbose_name_plural = _(
    "Outstanding tokens"
)
