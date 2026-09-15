# ممیزی الزامات پروژه Nexora

مرجع: `final_project_119.pdf`، بررسی کد موجود در ۱۵ سپتامبر ۲۰۲۶.

## نتیجه‌ی ممیزی

| الزام | وضعیت | توضیح |
|---|---|---|
| Custom user model و manager | انجام شده | `customers.Customer` و `CustomerManager` |
| ورود با username/email و رمز | انجام شده | backend اختصاصی و API احراز هویت |
| JWT در HttpOnly Cookie، refresh و logout | انجام شده | access/refresh cookie با CSRF |
| ثبت‌نام، پروفایل و تغییر رمز | انجام شده | API و صفحات account/profile |
| OTP ایمیلی، hash، انقضا و rate limit | انجام شده | cache/Redis و UI ورود دومرحله‌ای |
| ایمیل واقعی | آماده‌ی production | SMTP باید با مقادیر واقعی `.env` تنظیم شود |
| نقش مدیر محصولات، ناظر و اپراتور | انجام شده | Group، Permission و نقش روی کاربر |
| تشخیص نقش و دسترسی Admin | انجام شده | نقش‌ها به `is_staff` و مسیر Admin متصل‌اند |
| پروفایل و پنل مشتری | انجام شده | اطلاعات شخصی، آدرس‌ها، سفارش‌ها و امنیت |
| آدرس پیش‌فرض، ویرایش و حذف | انجام شده | API و UI checkout/profile |
| دسته‌بندی self-relation و نمایش درختی | انجام شده | serializer تو در تو و منوی بازشونده‌ی فرانت‌اند |
| محصول، برند، مشخصات و موجودی | انجام شده | API عمومی و seed کاتالوگ |
| تخفیف درصدی/نقدی و سقف درصدی | انجام شده | مدل، serializer، محاسبه و تست |
| کد تخفیف سبد | انجام شده | حداقل مبلغ، تاریخ و محدودیت مصرف |
| سبد مهمان و کاربر و ادغام پس از ورود | انجام شده | session cart و merge به customer cart |
| سبد خرید Single Page با DRF | انجام شده | تغییر تعداد و حذف بدون reload |
| ثبت سفارش فقط برای کاربر واردشده | انجام شده | checkout با `IsAuthenticated` |
| snapshot آیتم سفارش و کنترل موجودی | انجام شده | قیمت/نام/SKU و قفل تراکنشی پرداخت |
| حذف منطقی | انجام شده | customer، address، category، product، discount و discount code |
| Celery cleanup کاربران تأییدنشده | انجام شده | task و schedule ساعتی؛ اجرای واقعی نیازمند worker/beat است |
| Redis و PostgreSQL | آماده‌ی اجرا | تنظیمات و Docker Compose موجود است؛ محیط فعلی local با SQLite/LocMem است |
| پنل Admin اختصاصی و مجوز نقش‌ها | انجام شده | branding، fieldsets، inline و permission mixin |
| صفحات 404 و 500 اختصاصی | انجام شده | handlerهای پروژه و template اختصاصی |
| چندزبانه واقعی و RTL/LTR | انجام شده | ترجمه‌ی مرکزی فارسی/انگلیسی و ترجمه‌ی محتوای داینامیک |
| Dark Mode صفحات storefront | انجام شده | CSS و script صفحات اصلی |
| تست مدل، API، نقش و Admin | انجام شده | ۱۳۵ تست موفق در آخرین اجرا |
| پوشش تست بالای ۸۰٪ | انجام شده | پوشش فعلی ۹۴٪ |
| Selenium مسیر خرید | اختیاری و انجام نشده | PDF آن را امتیازی معرفی کرده است، نه الزام تحویل |
| ERD داخل مخزن | انجام شده | `docs/ERD.md` با Mermaid |
| README تحویل | انجام شده | اجرای local، Docker، API، تست و وضعیت محیطی مستند شده |
| شاخه‌ی `develop` | انجام شده | شاخه‌ی توسعه‌ی فعلی |
| شاخه‌ی `master` و merge فازها | نیازمند اقدام Git | باید در remote/فرآیند تحویل ایجاد و از `develop` merge شود |

## محدودیت‌های محیطی

برای تحویل واقعی هنوز این موارد خارج از کد باید روی محیط مقصد انجام شوند:

1. تنظیم SMTP واقعی و دامنه/گواهی HTTPS در production.
2. اجرای PostgreSQL، Redis، Celery worker و Celery beat.
3. اجرای migration، `seed_roles` و `seed_nexora` روی محیط مقصد.
4. ایجاد/به‌روزرسانی شاخه‌ی `master` و push commitها به remote.

## اعتبارسنجی آخرین دور

- `manage.py check`: موفق
- `makemigrations --check --dry-run`: بدون migration جاافتاده
- `manage.py test`: ۱۳۵ تست، همگی موفق
- Coverage: ۹۴٪
- syntax تمام فایل‌های JavaScript: موفق
- `git diff --check`: موفق
