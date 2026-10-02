# Nexora Online Store

فروشگاه آنلاین لوازم دیجیتال با Django، Django REST Framework، JWT در کوکی‌های `HttpOnly` و فرانت‌اند JavaScript مبتنی بر همان APIها.

## قابلیت‌های پیاده‌سازی‌شده

- کاربر اختصاصی، ثبت‌نام، ورود با username یا email، خروج و تغییر رمز عبور
- ورود دومرحله‌ای با OTP ایمیلی، ذخیره‌ی hash کد در cache و محدودیت درخواست
- نقش‌های مدیر محصولات، ناظر و اپراتور با Group و مجوزهای Django Admin
- پروفایل، آدرس‌های چندگانه، آدرس پیش‌فرض و حذف امن حساب با anonymize اطلاعات شخصی و امکان ثبت‌نام دوباره با همان ایمیل/نام کاربری
- دسته‌بندی درختی، جست‌وجو، فیلتر، موجودی و تخفیف درصدی/مبلغی
- کمپین‌های تخفیف زمان‌دار با نمایش پایان پیشنهاد و شمارش معکوس روی ویترین
- اعلان کاهش قیمت و برگشت موجودی با ایمیل، آستانه‌ی قیمت و Celery
- باشگاه امتیازی Nexora Club با ثبت خودکار امتیاز برای سفارش پرداخت‌شده و تاریخچه‌ی امتیازها
- مقایسهٔ حداکثر سه محصول با نمایش کنارهمی مشخصات، قیمت، موجودی و تخفیف
- سبد خرید مهمان و کاربر، ادغام سبد بعد از ورود، کوپن و تسویه‌حساب
- زمان‌بندی تحویل در checkout؛ انتخاب تاریخ از دو تا هفت روز بعد و بازه‌ی صبح یا عصر
- سفارش با snapshot اطلاعات محصول و کنترل موجودی هنگام پرداخت
- خرید مجدد سریع از تاریخچه سفارش با کنترل دوباره‌ی موجودی و وضعیت محصول
- پنل مشتری یکپارچه‌ی پروفایل، تاریخچه سفارش و پنل Admin سفارشی
- امتیازدهی و نقد محصول، رأی مفید بودن نقدها، نظرسنجی تجربه خرید و بخش پرسش‌های متداول تعاملی
- پرسش‌وپاسخ عمومی برای هر محصول با امکان پاسخ‌گویی تیم از پنل Admin
- نشان «خرید تأییدشده» برای نظرهایی که به سفارش پرداخت‌شده‌ی همان محصول متصل‌اند
- مقایسه محصولات، علاقه‌مندی‌ها، محصولات اخیراً دیده‌شده و نوار پیشرفت ارسال رایگان
- فیلتر هوشمند کاتالوگ برای محصولات تخفیف‌دار، موجودی و بازه قیمت به‌همراه مرتب‌سازی
- پیشنهادهای مرتبط در صفحه محصول بر اساس دسته‌بندی و سیگنال‌های امتیاز/تخفیف
- فارسی/انگلیسی واقعی، RTL/LTR، Dark Mode و صفحات 404/500 اختصاصی
- OpenAPI/Swagger/ReDoc، health check و Celery Beat برای cleanup کاربران تأییدنشده
- تمام مدل‌های پروژه در Admin با list display، فیلتر، جست‌وجو، fieldset/inline مناسب و دسترسی نقش‌محور ثبت شده‌اند

نقشه‌ی مدل‌ها در [docs/ERD.md](docs/ERD.md) و مسیرهای تجربه‌ی کاربر در [docs/storefront-storyboard.md](docs/storefront-storyboard.md) قرار دارد.

## اجرای محلی با SQLite

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py seed_roles
python manage.py seed_nexora
python manage.py runserver
```

آدرس‌های مهم:

- فروشگاه: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/api/docs/`
- ReDoc: `http://127.0.0.1:8000/api/redoc/`
- وضعیت سرویس: `http://127.0.0.1:8000/health/`

## API نسخه‌دار

تمام APIها زیر `/api/v1/` هستند:

| بخش | مسیر |
|---|---|
| محصولات و دسته‌بندی‌ها | `/api/v1/products/` و `/api/v1/categories/` |
| احراز هویت و پروفایل | `/api/v1/auth/`؛ ورود با username/password یا email/OTP برای مشتری |
| علاقه‌مندی، اعلان محصول، نظر، پرسش‌وپاسخ و بازخورد مشتری | `/api/v1/auth/favorites/`، `/api/v1/auth/product-watches/`، `/api/v1/products/{slug}/reviews/`، `/api/v1/products/{slug}/reviews/{review_id}/helpful/`، `/api/v1/products/{slug}/questions/`، `/api/v1/products/{slug}/questions/{question_id}/answer/` و `/api/v1/auth/feedback/` |
| سبد خرید | `/api/v1/cart/` |
| سفارش‌های مشتری و خرید مجدد | `/api/v1/orders/` و `/api/v1/orders/{order_number}/reorder/` |
| باشگاه امتیازی مشتری | `/api/v1/auth/rewards/` |
| سفارش‌های پنل | `/api/v1/admin/orders/` |

Access و refresh token در کوکی‌های `HttpOnly` ذخیره می‌شوند و درخواست‌های تغییردهنده از CSRF cookie استفاده می‌کنند.

## PostgreSQL، Redis و Celery با Docker

ابتدا باید Docker Compose Plugin نسخه ۲ فعال باشد و این دستور بدون خطا اجرا شود:

```bash
docker compose version
```

اگر خروجی `unknown command: docker compose` بود، Compose Plugin روی سیستم نصب نیست و باید از راهنمای توزیع Linux نصب شود.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

سرویس `web` روی پورت `8000` و HTTPS محلی از طریق Caddy روی پورت `8443` اجرا می‌شود.
آدرس اصلی برای تست مرورگر:

```text
https://localhost:8443/
```

Caddy برای localhost یک گواهی داخلی می‌سازد؛ بنابراین ممکن است اولین بار مرورگر
هشدار گواهی نشان دهد. برای خروجی گرفتن از CA داخلی Caddy و واردکردن آن در سیستم
عامل یا مرورگر:

```bash
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./docker/caddy/root.crt
```

در صورت نیاز، فایل `root.crt` را به عنوان گواهی ریشهٔ مورد اعتماد سیستم/مرورگر
اضافه کن. مسیر HTTP روی `http://127.0.0.1:8000/` نیز برای عیب‌یابی مستقیم web
در دسترس می‌ماند.

بعد از بالا آمدن سرویس‌ها، migration و seed را اجرا کن:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_roles
docker compose exec web python manage.py seed_nexora
```

برای فعال بودن پردازش‌های پس‌زمینهٔ اعلان‌ها، امتیازها و cleanup کاربران، worker
و beat را هم اجرا کن:

```bash
docker compose up -d worker beat
```

وضعیت health سرویس web را می‌توانی از این مسیر بررسی کنی:

```text
https://localhost:8443/health/
```

در Compose، web پشت Caddy با `X-Forwarded-Proto` اجرا می‌شود و کوکی‌های احراز
هویت، session و CSRF برای مسیر HTTPS با `Secure=True` تنظیم می‌شوند. اجرای مستقیم
`python manage.py runserver` همچنان از تنظیمات HTTP محلی استفاده می‌کند.

برای بررسی اولیه‌ی زیرساخت بدون اجرای taskهای زمان‌بندی‌شده، ابتدا فقط سرویس‌های
`db`، `redis` و `web` را اجرا کن:

```bash
docker compose up -d --build db redis web
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_roles
docker compose exec web python manage.py seed_nexora
```

در compose، PostgreSQL و Redis فقط داخل شبکه‌ی Docker در دسترس‌اند و فقط web روی
`127.0.0.1:8000` منتشر می‌شود. اگر Docker Hub از شبکه‌ی تو در دسترس نیست، imageها
را با mirror مورداعتماد خودت از طریق متغیرهای زیر override کن؛ این تغییر نیازی به
ویرایش فایل compose ندارد:

```bash
POSTGRES_IMAGE=your-trusted-mirror/postgres:16-alpine \
REDIS_IMAGE=your-trusted-mirror/redis:7-alpine \
CADDY_IMAGE=your-trusted-mirror/caddy:2-alpine \
docker compose up -d --build
```

برای ایمیل واقعی در production باید `EMAIL_HOST`، `EMAIL_PORT`، `EMAIL_HOST_USER`، `EMAIL_HOST_PASSWORD`، `DEFAULT_FROM_EMAIL` و `CSRF_TRUSTED_ORIGINS` واقعی تنظیم شوند. در local ایمیل‌ها به console backend می‌روند.

## اجرای بدون Docker در محیط محلی

اگر فعلاً Docker را اجرا نمی‌کنی، PostgreSQL و Redis را به‌صورت سرویس محلی
بالا بیاور و سپس Celery را جداگانه اجرا کن. برای HTTPS توسعه‌ای نیز دستور
`runhttps` با خود Python و `openssl` گواهی self-signed محلی می‌سازد و به package
اضافی یا reverse proxy نیاز ندارد:

```bash
# بررسی Redis؛ باید PONG برگرداند
redis-cli ping

# ترمینال اول: Django روی HTTPS محلی
./.venv/bin/python manage.py runhttps 127.0.0.1:8443

# ترمینال دوم: Celery worker
./.venv/bin/celery -A config worker -l INFO

# ترمینال سوم: Celery beat
./.venv/bin/celery -A config beat -l INFO
```

سایت در این حالت از مسیر زیر در دسترس است:

```text
https://127.0.0.1:8443/
```

مرورگر برای گواهی self-signed هشدار نشان می‌دهد؛ این رفتار برای محیط توسعه
طبیعی است. گواهی و کلید در `.local-certs/` ساخته می‌شوند و وارد Git نمی‌شوند.

## بررسی کیفیت

```bash
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
coverage run manage.py test
coverage report -m

# تست مرورگر واقعی مسیر خرید (نیازمند Chrome و ChromeDriver هم‌نسخه)
RUN_SELENIUM=1 CHROMEDRIVER_PATH=/path/to/chromedriver python manage.py test config.test_selenium
```

اگر Selenium Manager روی سیستم driver هماهنگ را پیدا نکرد، مقدار `CHROMEDRIVER_PATH` را به مسیر ChromeDriver هم‌نسخه با Chrome تنظیم کن.

## فازبندی Git

توسعه روی `develop` انجام می‌شود و نسخه‌ی نهایی هر فاز باید در `master` merge شود. commitهای هر فاز باید قبل از جلسه‌ی تحویل روی remote push شوند.

## موارد محیطی تحویل

- production واقعی به Redis، PostgreSQL، worker/beat و SMTP معتبر نیاز دارد.
- ۱۱ تست Selenium برای خرید، مقایسه، دارک‌مود، علاقه‌مندی، محصولات اخیراً دیده‌شده، پیشنهادهای مرتبط، بازخورد، فیلتر کاتالوگ و FAQ در `config/test_selenium.py` قرار دارد و با `RUN_SELENIUM=1` اجرا می‌شود.
- Docker Compose باید روی سیستم مقصد نصب و فعال باشد.
