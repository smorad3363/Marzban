# Marzban `v5.0.0-rc.9`

## اصلاح‌ها

- نصب و `marzban update` بدون نسخه، جدیدترین GitHub Release منتشرشده را—including
  prerelease—resolve می‌کنند و همان tag immutable را برای اسکریپت، فایل‌های نصب و
  image به کار می‌برند.
- نصب تازه بعد از health check تمام می‌شود و دیگر داخل log follow باقی نمی‌ماند.
- فرمان امن `marzban create-owner USERNAME` ساخت یا بازیابی Owner اولیه را انجام
  می‌دهد.
- dependencyهای واقعی بیلد dashboard قفل شده‌اند و CI اختلاف build committed با
  build تولیدشده را رد می‌کند.
- ورودی عددی Chakra دیگر `selectionStart` را روی DOM input از نوع `number` اجرا
  نمی‌کند.

## دیتابیس

schema، migration، query، index و accounting تغییر نکرده‌اند.
