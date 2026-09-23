from datetime import timedelta
from pathlib import Path

import environ


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(PROJECT_ROOT / ".env")

SECRET_KEY = env("SECRET_KEY", default="unsafe-development-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "core",
    "customers",
    "products",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_ROOT / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default=f"sqlite:///{PROJECT_ROOT / 'db.sqlite3'}",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa"
LANGUAGES = (
    ("fa", "فارسی"),
    ("en", "English"),
)
LOCALE_PATHS = [PROJECT_ROOT / "locale"]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [PROJECT_ROOT / "static"]
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_ROOT / "media"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=20)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default=EMAIL_HOST_USER or "no-reply@nexora.local",
)

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=env("REDIS_URL", default="redis://127.0.0.1:6379/1"))
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_BEAT_SCHEDULE = {
    "deactivate-unverified-customers": {
        "task": "customers.tasks.deactivate_unverified_customers",
        "schedule": 60 * 60,
    },
    "send-product-watch-notifications": {
        "task": "customers.tasks.send_product_watch_notifications",
        "schedule": 15 * 60,
    },
    "issue-birthday-discount-notifications": {
        "task": "customers.tasks.issue_birthday_discount_notifications",
        "schedule": 60 * 60 * 24,
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "customers.Customer"
AUTHENTICATION_BACKENDS = (
    "customers.authentication.CustomerAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
)

AUTH_COOKIE_ACCESS = env("AUTH_COOKIE_ACCESS", default="access_token")
AUTH_COOKIE_REFRESH = env("AUTH_COOKIE_REFRESH", default="refresh_token")
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=False)
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "customers.authentication.CookieJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.NexoraPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "120/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Nexora Store API",
    "DESCRIPTION": "Professional commerce API for the Nexora digital accessories store.",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_INCLUDE_SCHEMA": False,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "nexora": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
