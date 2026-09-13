from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Customer


@shared_task
def deactivate_unverified_customers(days=3):
    cutoff = timezone.now() - timedelta(days=days)
    queryset = Customer.objects.filter(
        is_active=True,
        email_verified=False,
        is_staff=False,
        is_superuser=False,
        date_joined__lt=cutoff,
    )
    updated = queryset.update(is_active=False)
    return updated
