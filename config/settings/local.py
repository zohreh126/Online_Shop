from .base import *


DEBUG = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
AUTH_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
