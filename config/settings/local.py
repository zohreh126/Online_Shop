import sys

from .base import *


DEBUG = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Local development normally runs over plain HTTP.  Docker Compose can put
# Caddy in front of the app and set these flags to use the same local settings
# behind HTTPS without forcing the browser cookies to be secure during the
# regular `runserver` workflow.
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)

if env.bool("TRUST_PROXY", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# The regular local server can use Redis for cache/OTP throttling. Tests run
# with the local settings in this project as well, so keep them deterministic
# and independent from a developer's Redis service.
_running_tests = bool(sys.argv[1:]) and sys.argv[1] == "test"

if _running_tests or not env.bool("USE_REDIS", default=False):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nexora-local-cache",
        }
    }
