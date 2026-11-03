# Nexora Store

فروشگاه آنلاین Nexora برای فروش لوازم جانبی کامپیوتر، تجهیزات صوتی، محصولات
گیمینگ و ابزارهای دیجیتال است. این پروژه یک storefront دو‌زبانه و یک backend
رابط‌محور ارائه می‌کند و بخش‌هایی مانند حساب کاربری، کاتالوگ، علاقه‌مندی، سبد
خرید، تخفیف، سفارش، اعلان و پنل مدیریت را پوشش می‌دهد.

## قابلیت‌ها

- رابط فارسی و انگلیسی با پشتیبانی واقعی از RTL و LTR
- حالت روشن و تاریک و طراحی واکنش‌گرا برای دسکتاپ و موبایل
- کاتالوگ محصول با جست‌وجو، فیلتر، مرتب‌سازی و صفحه‌بندی
- نمایش تصاویر محصول، محصولات مرتبط و مقایسهٔ محصولات
- حساب کاربری با ورود نام کاربری/رمز عبور یا ایمیل و کد یک‌بارمصرف
- JWT در کوکی‌های `HttpOnly` به‌همراه حفاظت CSRF
- سبد خرید مهمان و ادغام آن با سبد کاربر پس از ورود
- علاقه‌مندی، پیگیری محصول، نظر، پرسش و امتیازدهی
- تخفیف محصول، کد تخفیف، محدودیت تاریخ و حداقل مبلغ خرید
- سفارش با snapshot اقلام، کنترل موجودی و هزینهٔ ارسال
- انتخاب تاریخ تحویل بین دو تا هفت روز آینده و بازهٔ زمانی صبح یا عصر
- اعلان داخل سایت و ارسال ایمیل برای رویدادهای حساب، سفارش و بازاریابی
- پنل مدیریت نقش‌محور برای کاربران، کاتالوگ، سفارش‌ها و تخفیف‌ها
- API نسخه‌دار با OpenAPI، Swagger و ReDoc
- PostgreSQL، Redis، Celery و Celery Beat برای اجرای کامل سرویس‌ها
- Docker Compose و Caddy برای اجرای سرویس‌ها و HTTPS محلی

## فناوری‌ها

| بخش | فناوری |
|---|---|
| زبان | Python 3.10+ |
| backend | Django 5.2 و Django REST Framework |
| احراز هویت | SimpleJWT، HttpOnly Cookie و CSRF |
| پایگاه داده | SQLite برای اجرای ساده، PostgreSQL برای اجرای سرویس‌محور |
| cache و broker | Redis |
| پردازش پس‌زمینه | Celery و Celery Beat |
| رابط کاربری | HTML، CSS و JavaScript |
| API documentation | drf-spectacular، OpenAPI، Swagger و ReDoc |
| تست مرورگر | Selenium و ChromeDriver هم‌نسخه |
| زیرساخت محلی | Docker Compose و Caddy |

## ساختار پروژه

```text
config/             تنظیمات، URLها، Celery و تست‌های یکپارچه
core/               مدل‌ها، health check، پنل و permissionهای مشترک
customers/          کاربر، احراز هویت، OTP، آدرس، اعلان و علاقه‌مندی
products/           دسته‌بندی، محصول، تخفیف، نظر و پرسش
orders/             سبد خرید، checkout، سفارش، ارسال و امتیازها
templates/          قالب‌های HTML
static/storefront/  CSS، JavaScript، تصاویر و رابط فروشگاه
static/admin/       CSS و JavaScript پنل مدیریت Nexora
docker/             تنظیمات Caddy
docs/               مستندات فنی منتخب پروژه
media/              محل فایل‌های رسانه‌ای محلی
Dockerfile
docker-compose.yml
manage.py
requirements.txt
```

## پیش‌نیازها

برای اجرای ساده:

- Python 3.10 یا بالاتر
- `python3-venv` و `pip`
- Git

برای اجرای کامل سرویس‌ها:

- PostgreSQL 16
- Redis 7
- Docker Engine و Docker Compose Plugin v2

برای تست مرورگر:

- Google Chrome یا Chromium
- ChromeDriver هم‌نسخه با مرورگر

## اجرای سریع با SQLite

```bash
git clone <repository-url>
cd Online_store

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env
```

در `.env` برای اجرای ساده، `USE_REDIS=False` قرار بده و `DATABASE_URL` را
تنظیم نکن تا SQLite استفاده شود. برای ایمیل محلی نیز می‌توانی از backend کنسول
استفاده کنی تا کد OTP در ترمینال نمایش داده شود.

سپس migration و دادهٔ اولیه را بساز:

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py seed_roles
./.venv/bin/python manage.py seed_nexora
./.venv/bin/python manage.py runserver
```

آدرس‌های اصلی:

- فروشگاه: <http://127.0.0.1:8000/>
- پنل مدیریت: <http://127.0.0.1:8000/admin/>
- Swagger: <http://127.0.0.1:8000/api/docs/>
- ReDoc: <http://127.0.0.1:8000/api/redoc/>
- OpenAPI schema: <http://127.0.0.1:8000/api/schema/>
- Health check: <http://127.0.0.1:8000/health/>

دستور `seed_nexora` idempotent است و اجرای دوبارهٔ آن داده‌های اولیهٔ
دسته‌بندی، محصول، تخفیف و کد تخفیف را همگام می‌کند.

## اجرای PostgreSQL و Redis

در `.env` مقدار اتصال را مطابق سرویس‌های سیستم قرار بده:

```dotenv
DATABASE_URL=postgresql://nexora:change-this-password@127.0.0.1:5432/nexora
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
USE_REDIS=True
```

سپس:

```bash
redis-cli ping
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py seed_roles
./.venv/bin/python manage.py seed_nexora
./.venv/bin/python manage.py runserver
```

## اجرای Docker Compose

Compose سرویس‌های `db`، `redis`، `web`، `caddy`، `worker` و `beat` را اجرا
می‌کند.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps

docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_roles
docker compose exec web python manage.py seed_nexora
```

آدرس‌های Compose:

- فروشگاه HTTPS: <https://localhost:8443/>
- دسترسی مستقیم web: <http://127.0.0.1:8000/>
- health check: <https://localhost:8443/health/>

گواهی Caddy با `tls internal` برای localhost ساخته می‌شود و ممکن است مرورگر در
اولین ورود هشدار گواهی نشان دهد. برای توقف سرویس‌ها:

```bash
docker compose down
```

## ایمیل و OTP

برای ارسال واقعی ایمیل، مقدارهای SMTP را در `.env` قرار بده. نمونهٔ تنظیمات در
فایل [راهنمای ایمیل](docs/email-setup.md) آمده است. رمز SMTP و App Password
نباید داخل Git ثبت شوند.

برای تست مستقل backend ایمیل:

```bash
./.venv/bin/python manage.py test_email your-address@example.com
```

## Celery Worker و Beat

وقتی Redis فعال است، worker و scheduler را جداگانه اجرا کن:

```bash
./.venv/bin/celery -A config worker -l INFO --pool=solo
./.venv/bin/celery -A config beat -l INFO
```

Worker taskهای پس‌زمینه مانند اعلان و ایمیل را اجرا می‌کند و Beat taskهای
زمان‌بندی‌شده را به صف می‌فرستد.

## APIهای اصلی

همهٔ APIها زیر مسیر `/api/v1/` قرار دارند. گروه‌های اصلی عبارت‌اند از:

- `/api/v1/auth/` برای ثبت‌نام، ورود، OTP، پروفایل، آدرس و اعلان
- `/api/v1/products/` برای کاتالوگ، دسته‌بندی، جست‌وجو، نظر و پرسش
- `/api/v1/cart/` برای سبد، کوپن و checkout
- `/api/v1/orders/` برای سفارش، نتیجهٔ پرداخت mock و خرید مجدد
- `/api/v1/admin/` برای عملیات مدیریتی نقش‌محور

مستندات تعاملی API از مسیرهای `/api/docs/` و `/api/redoc/` قابل مشاهده است.

## تست و کنترل کیفیت

اجرای بررسی‌های پایه:

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
./.venv/bin/python manage.py test
```

تست مرورگر به‌صورت opt-in اجرا می‌شود و به ChromeDriver هم‌نسخه نیاز دارد:

```bash
RUN_SELENIUM=1 \
CHROMEDRIVER_PATH=/path/to/chromedriver \
./.venv/bin/python manage.py test config.test_selenium -v 2
```

## مدل داده

نمودار ارتباط موجودیت‌های اصلی در [docs/ERD.md](docs/ERD.md) قرار دارد. در
مدل سفارش، نام، SKU، قیمت و تخفیف هر کالا هنگام ثبت خرید snapshot می‌شوند تا
تغییرات بعدی کاتالوگ روی سفارش‌های قبلی اثر نگذارد.

## ملاحظات امنیتی و عملیاتی

- `.env`، کلیدها، رمز SMTP، دیتابیس محلی، cache و گواهی‌های محلی در Git نگهداری
  نمی‌شوند.
- در محیط واقعی `SECRET_KEY`، رمزهای دیتابیس و credentialهای SMTP باید از secret
  manager یا متغیر محیطی امن تأمین شوند.
- پرداخت فعلی mock است و برای اتصال به درگاه واقعی باید gateway، callback و
  مدیریت تراکنش ناموفق اضافه شود.
- HTTPS موجود در Compose برای localhost است؛ برای دامنهٔ عمومی باید گواهی معتبر
  و تنظیمات production استفاده شود.
- برای اجرای چندپردازه و اعلان‌های واقعی، Redis و worker پایدار لازم هستند.
- قبل از استقرار عمومی، backup، logging، monitoring، محدودسازی hostها و storage
  رسانه باید مطابق محیط مقصد تنظیم شوند.

## مستندات فنی

- [نمودار ERD](docs/ERD.md)
- [تنظیم ایمیل و OTP](docs/email-setup.md)

## مجوز

این کد برای استفاده و توسعهٔ Nexora منتشر شده است. استفادهٔ تجاری از نام تجاری،
تصاویر و داده‌های نمونه باید جداگانه بررسی شود.
