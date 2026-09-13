# Nexora Online Store

فروشگاه آنلاین Nexora با Django، Django REST Framework و احراز هویت JWT در کوکی HttpOnly.

## اجرای محلی با SQLite

محیط محلی به‌صورت پیش‌فرض از SQLite و cache داخل حافظه استفاده می‌کند:

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py seed_nexora
python manage.py runserver
```

## اجرای PostgreSQL و Redis با Docker

Docker فقط سرویس‌های زیرساختی PostgreSQL و Redis را اجرا می‌کند؛ خود Django همچنان با محیط مجازی محلی اجرا می‌شود.

```bash
cp .env.example .env
docker compose up -d db redis
docker compose ps
```

پس از آماده‌شدن سرویس‌ها، در `.env` مقدارهای اتصال را بررسی کن و سپس:

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py seed_roles
python manage.py seed_nexora
python manage.py runserver
```

برای توقف سرویس‌ها:

```bash
docker compose down
```

برای حذف volumeهای داده‌ی محلی PostgreSQL و Redis، فقط در صورت نیاز اجرا کن:

```bash
docker compose down -v
```

## بررسی کیفیت

```bash
python manage.py check
python manage.py check --deploy
python manage.py test
```

برای بررسی تولید، از `config.settings.production` همراه با `SECRET_KEY` طولانی، `ALLOWED_HOSTS` و `CSRF_TRUSTED_ORIGINS` واقعی استفاده کن.
