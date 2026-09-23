import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Customer, CustomerNotification


logger = logging.getLogger(__name__)


def active_marketing_customers():
    return Customer.objects.filter(
        is_active=True,
        is_staff=False,
        is_superuser=False,
    ).exclude(email="")


def create_notification(customer, *, kind, title, body, link=""):
    return CustomerNotification.objects.create(
        customer=customer,
        kind=kind,
        title=title,
        body=body,
        link=link,
    )


def send_customer_email(customer, *, subject, body):
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [customer.email],
            fail_silently=False,
        )
        return True
    except Exception:  # pragma: no cover - SMTP failures belong in logs, not checkout failures.
        logger.exception("Marketing email failed for customer %s", customer.pk)
        return False


def broadcast_store_message(*, kind, title, body, link="", subject=None):
    """Create an in-site notification and attempt a real email for each member."""
    delivered = 0
    for customer in active_marketing_customers().iterator():
        create_notification(customer, kind=kind, title=title, body=body, link=link)
        if send_customer_email(customer, subject=subject or title, body=body):
            delivered += 1
    return delivered
