import logging
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.mail import send_mail


OTP_TTL = 5 * 60
OTP_MAX_ATTEMPTS = 5
OTP_MAX_REQUESTS = 3
OTP_REQUEST_WINDOW = 10 * 60
logger = logging.getLogger("nexora.auth")


class OTPDeliveryError(Exception):
    """Raised when the verification code cannot be delivered by email."""


def _otp_key(email):
    return f"nexora:otp:{email}"


def _rate_key(email):
    return f"nexora:otp-rate:{email}"


def request_otp(email):
    email = email.strip().lower()
    rate_key = _rate_key(email)
    cache.add(rate_key, 0, timeout=OTP_REQUEST_WINDOW)
    request_count = cache.incr(rate_key)

    if request_count > OTP_MAX_REQUESTS:
        raise ValueError("Too many OTP requests. Try again later.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    cache.set(
        _otp_key(email),
        {"hash": make_password(code), "attempts": 0},
        timeout=OTP_TTL,
    )

    try:
        send_mail(
            subject="Nexora verification code",
            message=(
                "Your Nexora verification code is: "
                f"{code}\n\nThis code expires in 5 minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        cache.delete(_otp_key(email))
        logger.exception("OTP delivery failed", extra={"recipient": email})
        raise OTPDeliveryError from exc


def verify_otp(email, code):
    key = _otp_key(email)
    payload = cache.get(key)

    if payload is None:
        raise ValueError("OTP is invalid or expired.")

    if payload["attempts"] >= OTP_MAX_ATTEMPTS:
        cache.delete(key)
        raise ValueError("Too many verification attempts. Request a new OTP.")

    if not check_password(code, payload["hash"]):
        payload["attempts"] += 1
        if payload["attempts"] >= OTP_MAX_ATTEMPTS:
            cache.delete(key)
        else:
            cache.set(key, payload, timeout=OTP_TTL)
        raise ValueError("OTP is invalid or expired.")

    cache.delete(key)
