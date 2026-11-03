# تنظیم ارسال ایمیل فروشگاه

در حالت پیش‌فرض توسعه، پروژه از `console.EmailBackend` استفاده می‌کند؛ بنابراین
کد OTP داخل ترمینال اجرای Django چاپ می‌شود و ایمیل واقعی ارسال نمی‌شود.

برای فعال‌کردن ارسال واقعی، فایل `.env` را با اطلاعات حساب ایمیل فروشگاه تنظیم
کن. فایل `.env` در Git ثبت نمی‌شود.

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=store@example.com
EMAIL_HOST_PASSWORD=app-password
DEFAULT_FROM_EMAIL=store@example.com
EMAIL_TIMEOUT=20
```

اگر از Gmail استفاده می‌کنی، باید تأیید دومرحله‌ای را فعال کنی و به‌جای رمز اصلی
از **App Password** استفاده کنی. برای سرویس‌های دیگر، `EMAIL_HOST` و پورت را
مطابق مستندات همان سرویس قرار بده.

بعد از ذخیره تنظیمات، برای تست مستقل از OTP اجرا کن:

```bash
./.venv/bin/python manage.py test_email your-address@example.com
```

اگر ارسال موفق باشد، پیام موفقیت در ترمینال نمایش داده می‌شود. پوشه Spam/Junk
را هم بررسی کن. خطاهای اتصال معمولاً از نادرست‌بودن میزبان، پورت، TLS یا App
Password هستند.
