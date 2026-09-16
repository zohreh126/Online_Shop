from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST_USER="store@example.com",
    DEFAULT_FROM_EMAIL="no-reply@nexora.local",
)
class EmailCommandTests(TestCase):
    def test_diagnostic_command_sends_from_configured_store_account(self):
        output = StringIO()

        call_command("test_email", "owner@example.com", stdout=output)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "store@example.com")
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("ارسال شد", output.getvalue())
