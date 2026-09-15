# Nexora project requirements audit

مرجع بررسی: `final_project_119.pdf` (شرح پروژه فروشگاه آنلاین مکتب).

## وضعیت پیاده‌سازی

| الزام | وضعیت | محل اصلی پیاده‌سازی |
|---|---|---|
| Custom user model | انجام شده | `customers.models.Customer` |
| ثبت‌نام و ویرایش اطلاعات مشتری | انجام شده | `customers/serializers.py`, `customers/views.py` |
| ورود با نام کاربری یا ایمیل و رمز عبور | انجام شده | `customers/authentication.py`, `customers/auth_views.py` |
| ورود دومرحله‌ای با OTP ایمیلی | انجام شده | `customers/otp.py`, `customers/auth_views.py`, `static/storefront/js/account.js` |
| ذخیره OTP در cache/Redis و محدودیت تلاش | انجام شده | `customers/otp.py`, تنظیمات cache |
| ارسال ایمیل واقعی در production | آماده | `config/settings/production.py` و متغیرهای SMTP در `.env.example` |
| نقش‌های مدیر محصولات، ناظر و اپراتور | انجام شده | `customers.models.Customer.Role`, `seed_roles` |
| تشخیص نقش و مسیر ورود | انجام شده | `account.js`, فیلد `role` پروفایل |
| پنل ادمین اختصاصی و سطح دسترسی نقش‌ها | انجام شده | `core/admin.py`, `core/admin_permissions.py`, adminهای appها |
| حذف منطقی رکوردهای قابل حذف | انجام شده | `is_active` و `RolePermissionAdminMixin` |
| دسته‌بندی self-relation و درختی | انجام شده | `products.models.Category`, serializer و `app.js` |
| محصول، موجودی، برند و مشخصات | انجام شده | `products.models.Product` |
| تخفیف درصدی/مبلغی و کد تخفیف | انجام شده | `products.models.Discount`, `DiscountCode` |
| سبد مهمان و سبد کاربر | انجام شده | `orders.cart_services`, APIهای cart |
| سبد خرید SPA با DRF | انجام شده | `orders/views.py`, `static/storefront/js/app.js` |
| کنترل موجودی و تعداد آیتم | انجام شده | مدل‌ها و serializerهای orders |
| ثبت سفارش با انتخاب آدرس | انجام شده | checkout API و `checkout.js` |
| تاریخچه و وضعیت سفارش در پنل مشتری | انجام شده | dashboard/profile و order API |
| آدرس‌های مشتری با ایجاد، ویرایش و حذف | انجام شده | `AddressViewSet`, profile/checkout JS |
| Celery برای حذف کاربر تأییدنشده بعد از ۳ روز | انجام شده | `customers.tasks`, Celery Beat |
| چندزبانه و RTL/LTR | انجام شده | `i18n.js`, قالب‌ها و CSS |
| دارک مود همه صفحات اصلی | انجام شده | `app.css` و اسکریپت‌های صفحات |
| داده نمونه و کاتالوگ توسعه‌یافته | انجام شده | `seed_nexora`; حداقل ۲۶ محصول فعال |
| تست API و مدل‌ها | انجام شده | testهای appها |
| پوشش تست بالای ۸۰٪ | انجام شده | آخرین اندازه‌گیری: ۹۴٪ |

## موارد محیطی قبل از تحویل

- برای ایمیل واقعی، مقادیر `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` و دامنه امن در `.env` production تنظیم شوند.
- برای اجرای کامل Celery، Redis و worker/beat باید با Docker یا سرویس‌های معادل فعال باشند.
- قبل از تحویل، `python manage.py migrate`, `seed_roles`, `seed_nexora`, `check --deploy` و تست کامل اجرا شوند.
- به‌دلیل read-only بودن مسیر `.git` در محیط فعلی، commit این دور باید در محیط توسعه‌ی اصلی ثبت شود.
