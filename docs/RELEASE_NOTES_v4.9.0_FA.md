# Marzban v4.9.0

این نسخه ساختار مدیریتی سلسله‌مراتبی را با سازگاری افزایشی برای نصب‌های قبلی اضافه می‌کند.

## قابلیت‌ها

- نقش‌های `OWNER`، `SUPER_ADMIN` و `ADMIN` با closure table و scope کامل subtree
- فعال‌سازی صریح و تراکنشی با `marzban set-owner <username>`
- دفترکل انتقال و بازپس‌گیری اعتبار حجم با idempotency و قفل‌گذاری منظم
- توکن Automation مستقل، hash‌شده، زمان‌دار و scope‌شده؛ API خارجی غیر Owner پیش‌فرض خاموش
- تعلیق و رفع تعلیق قابل‌بازگشت با snapshot وضعیت کاربران و قطع خودکار انقضا/اتمام اعتبار
- bulk disable قابل‌ادامه با cursor و commitهای chunked
- Planهای نسخه‌دار و تغییرناپذیر، allowlist شاخه، `PLAN_ONLY`، ساخت و تمدید idempotent
- scope یکپارچه کاربران، آمار، audit، device-limit و مخفی‌سازی زیرساخت برای غیر Owner
- داشبورد responsive برای حساب، درخت مدیریت، اعتبار، تعلیق و Planها
- دیالوگ مستقل تمدید User با Plan از داخل فهرست کاربران
- audit عملیات حساس، conflict-safe idempotency و query ثابت بدون N+1 برای درخت Adminها

## ارتقا و بازگشت

- migration `e2a6c1f4b903` افزایشی و feature flag در ابتدا خاموش است.
- تا اجرای موفق `marzban set-owner <username>` رفتار legacy فعال می‌ماند.
- image `v4.8.0` ستون‌ها و جدول‌های افزوده را نادیده می‌گیرد؛ CI اتصال نسخه قبلی به schema جدید را بررسی می‌کند.
- release workflow پیش از انتشار، MySQL 8.0، partial DDL recovery، rerun، backup/checksum/restore و rollback compatibility را اجرا می‌کند.

## نکته عملیاتی

پیش از cutover از دیتابیس backup بگیرید، سپس migration را اجرا و در پایان Owner را تعیین کنید. تغییر Owner یا downgrade schema در production بدون backup تأییدشده توصیه نمی‌شود.
