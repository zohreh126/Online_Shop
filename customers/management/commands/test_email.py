from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a diagnostic email using the configured Nexora email backend."

    def add_arguments(self, parser):
        parser.add_argument(
            "recipient",
            help="Email address that should receive the diagnostic message.",
        )
        parser.add_argument(
            "--subject",
            default="Nexora email configuration test",
            help="Optional subject for the diagnostic message.",
        )

    def handle(self, *args, **options):
        recipient = options["recipient"].strip()
        if not recipient or "@" not in recipient:
            raise CommandError("یک آدرس ایمیل معتبر برای گیرنده وارد کن.")

        sender = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
        if not sender:
            raise CommandError(
                "فرستنده ایمیل تنظیم نشده است؛ EMAIL_HOST_USER یا "
                "DEFAULT_FROM_EMAIL را در .env مقداردهی کن."
            )

        message = EmailMessage(
            subject=options["subject"],
            body=(
                "This is a Nexora email configuration test.\n\n"
                "If you received this message, SMTP delivery is working."
            ),
            from_email=sender,
            to=[recipient],
        )

        try:
            message.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(
                "ارسال ایمیل انجام نشد؛ HOST، PORT، TLS و اطلاعات حساب را بررسی کن. "
                f"جزئیات: {exc}"
            ) from exc

        backend_name = settings.EMAIL_BACKEND.rsplit(".", 1)[-1]
        self.stdout.write(
            self.style.SUCCESS(
                f"ایمیل آزمایشی با backend={backend_name} از {sender} "
                f"به {recipient} ارسال شد."
            )
        )
