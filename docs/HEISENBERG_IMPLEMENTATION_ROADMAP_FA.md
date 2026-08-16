<div dir="rtl" align="right">

# نقشه راه و وضعیت پیاده‌سازی هایزنبرگ

آخرین به‌روزرسانی: `2026-08-17`

وضعیت کلی: **پیاده‌سازی و آزمون محلی کامل؛ آمادهٔ انتشار immutable با tag `v4.7.0`. آزمون MySQL در release gate اجرا می‌شود.**

## دامنه و خط قرمز

- درخواست مستقیم کاربر: معماری، پایگاه‌داده و ارتباطات هر سه پروژهٔ `Marzban`، `marzhelp` و `V2IpLimit` بررسی شود.
- تنها محل مجاز تغییر: `C:\Users\Saji\Desktop\vProject\Marzban`
- `marzhelp` و `V2IpLimit` فقط مرجع خواندنی بوده‌اند و هیچ فایلی در آن‌ها تغییر نکرده است.
- سند مشخصات: `C:\Users\Saji\Downloads\Updated Marzban - Heisenberg Implementation Prompt.md`
- کامیت آغازین `Marzban`: `00a59e194e14afdd2a001d3bbc3bef74d64abe02`
- کامیت مرجع `marzhelp`: `d7af880d96a55fc800b6558008c54c5106f512a5`
- کامیت مرجع `V2IpLimit`: `6d68f169491c820edc1c147c80e883603e5c8318`
- شاخهٔ محلی از ابتدا نسبت به `origin/master` دارای تاریخچهٔ متفاوت و تغییرات کاربر بود. هیچ عملیات `merge`، `rebase`، `reset`، `commit` یا `push` انجام نشده است.
- ورودی‌های از قبل موجود و بدون رهگیری مانند `.codex/`، `AGENTS.md`، `design-system/` و `graphify-out/` متعلق به کاربر و حفظ شده‌اند.

## وضعیت مراحل

- [x] مرحله ۰ — ثبت خط پایه، وضعیت Git، نسخه‌ها و ابزارها
- [x] مرحله ۱ — بررسی معماری، مدل‌ها، API، رابط، نصب و جریان Xray در `Marzban`
- [x] مرحله ۲ — بررسی خواندنی `marzhelp` و قراردادهای ادغام‌شده
- [x] مرحله ۳ — بررسی خواندنی `V2IpLimit` و منطق IP، log و lifecycle
- [x] مرحله ۴ — طراحی و مهاجرت schema/API سازگار با SQLite و MySQL/InnoDB
- [x] مرحله ۵ — Device Limit، User-Agent، risk، handoff و warning lifecycle
- [x] مرحله ۶ — سهمیه‌های مدیر، ledger، حذف مدیر و ترمیم orphanها
- [x] مرحله ۷ — رفع EOF و health check داخلی/عمومی
- [x] مرحله ۸ — رابط هایزنبرگ و ترجمهٔ فارسی
- [x] مرحله ۹ — تست backend، هم‌زمانی، migration، type-check و build رابط
- [x] مرحله ۱۰ — بازبینی امنیت، کارایی پایگاه‌داده و سازگاری عقب‌رو

## یافته‌های معماری سه پروژه

- `Marzban` مالک schema و دادهٔ اصلی است. مدل‌ها، مهاجرت‌ها، CRUD، API، Xray و رابط در همین مخزن قرار دارند.
- `marzhelp` schema مستقل نمی‌سازد؛ با ردیف‌های متعلق به `Marzban` عملیات DML انجام می‌دهد. بنابراین هیچ تغییر جداگانه‌ای در آن لازم یا مجاز نبود.
- `V2IpLimit` پایگاه‌دادهٔ مستقل ندارد؛ logهای اتصال را مصرف و از REST برای مجازات استفاده می‌کند. state پایدار، audit پایدار و lifecycle کامل ندارد.
- ریشهٔ محتمل و سپس تست‌شدهٔ EOF، عبور دادن ORM object وابسته به request به background task بود. عملیات Xray اکنون با `user_id` یک session تازه باز می‌کند.
- معنای قدیمی `max_users` ظرفیت وزن‌دار دستگاه بود. اکنون `max_users` شمار حساب است و ظرفیت وزن‌دار در `device_capacity_limit` مستقل نگهداری می‌شود.
- health check قدیمی به `127.0.0.1:8000` ثابت بود. اکنون پورت داخلی از `UVICORN_PORT` و نشانی عمومی از تنظیم صریح یا `XRAY_SUBSCRIPTION_URL_PREFIX` مشتق می‌شود.

## پیاده‌سازی انجام‌شده

### Device Limit و مشاهدهٔ کلاینت

- capabilityهای مستقل: `device_slots_enabled`، `ip_detection_enabled` و `client_fingerprint_enabled`
- حفظ `enforcement_mode` فقط برای سازگاری ورودی و مهاجرت قدیمی
- parser محدودشدهٔ User-Agent برای خانواده‌های رایج، با raw حداکثر `512` نویسه
- observation تجمیعی در سطح slot و fallback سطح user، بدون ذخیرهٔ credential
- یکسان‌سازی نسخه‌های patch در هویت نرمال‌شده
- تفکیک اتصال fresh و stale، حداقل اتصال موفق، handoff grace و pending handoff
- عدم افزایش strike در `pending_handoff`
- لغو pending در جابه‌جایی معتبر و تأیید تخلف فقط با هم‌زمانی fresh پس از grace
- محاسبهٔ risk از IP، خانوادهٔ کلاینت، platform و slot
- ممنوعیت مجازات مخرب صرفاً بر پایهٔ User-Agent
- lifecycleهای `pending_handoff`، `warning`، `confirmed_violation`، `temporarily_disabled`، `permanently_disabled`، `resolved` و `expired`
- پاک‌سازی خودکار فقط برای warning منقضی و حذف دستی فقط با مجوز مالک یا sudo

### سهمیه، ledger و مدیریت مدیر

- شمار حساب، ظرفیت وزن‌دار دستگاه، حجم provisioning و سهمیهٔ renewal کاملاً مستقل‌اند.
- `NULL` برای سهمیه‌های اختیاری به معنی unlimited حفظ شده است.
- مصرف با row lock و compare-and-swap انجام می‌شود؛ مسابقهٔ آخرین ظرفیت تست شده است.
- create سهم حساب و حجم provisioning را مصرف می‌کند؛ renewal فقط عملیات تعریف‌شدهٔ تمدید را مصرف می‌کند.
- ویرایش عادی renewal مصرف نمی‌کند.
- transfer، delete و next-plan activation شمارنده‌های مربوط را تنظیم می‌کنند.
- ledger شامل `volume_delta`، `renewal_delta` و `result` است.
- رد سهمیه پس از rollback تراکنش درخواست، با `result="rejected"` در تراکنش audit جدا ذخیره می‌شود.
- کلیدهای عملیات موفق برای جلوگیری از دوباره‌شارژ شدن یکتا هستند.
- سه راهبرد حذف مدیر پیاده شده است: `delete_users`، `disable_users` و `keep_users`.
- در دو حالت نگهداری، مالکیت جدا می‌شود تا sudo همچنان کاربر را مدیریت کند.
- repair برای orphanهای قدیمی هم در migration و هم endpoint مدیریتی وجود دارد.

### EOF، health و رابط

- background taskهای Xray دیگر ORM object جداشده دریافت نمی‌کنند؛ session تازه بر اساس `user_id` باز می‌شود.
- `scripts/healthcheck.py` حالت‌های `internal`، `public` و `all` دارد و TLS verification به‌طور پیش‌فرض فعال است.
- `docker-compose.yml` و `scripts/marzban.sh` از helper جدید و تنظیمات واقعی استفاده می‌کنند.
- داشبورد capabilityها، زمان‌بندی handoff، عمر warning، lifecycle/risk، کلاینت هر slot، خلاصهٔ سهمیه و راهبرد حذف مدیر را نمایش می‌دهد.
- مقدار unlimited با مقدار واقعی نامحدود نمایش داده می‌شود؛ عدد بزرگ جعلی استفاده نشده است.
- raw User-Agent فقط وقتی backend مجاز بداند برگردانده می‌شود و React آن را به‌صورت متن escape می‌کند.

## schema و migration

- migration جدید: `app/db/migrations/versions/d7f3a2c9e104_heisenberg_capabilities_and_quotas.py`
- شناسه: `d7f3a2c9e104`
- والد: `b64e91d7c2a4`
- head فعلی: `d7f3a2c9e104`
- جدول جدید: `device_client_observations`
- index جدید: `ix_device_client_observation_user_slot_seen`
- indexهای query/FK: `ix_device_client_observation_user_seen` و `ix_device_client_observation_slot`
- index پاک‌سازی هشدار: `ix_device_limit_incidents_warning_expiry`
- ستون‌های capability و زمان‌بندی به `device_limit_settings`
- ستون‌های pending به `device_limit_user_states`
- ستون‌های lifecycle/risk/expiry به `device_limit_incidents`
- ستون‌های شمار، ظرفیت، حجم و renewal به `marzhelp_admin_settings`
- ستون‌های حجم، renewal و نتیجه به `marzhelp_accounting_transactions`
- مهاجرت idempotent برای تحمل DDL نیمه‌کارهٔ MySQL نوشته شده است.
- نگاشت قدیمی: `slots` به slot روشن/IP خاموش؛ `ip` و `hybrid` به slot و IP روشن؛ fingerprint در هر سه خاموش تا مدیر صریحاً فعال کند.
- orphanهای `users.admin_id` به `NULL` ترمیم می‌شوند.

## فایل‌های اصلی تغییرکرده

- backend و schema: `app/db/models.py`، `app/db/crud.py`، `app/utils/marzhelp_policy.py`
- Device Limit: `app/device_limit/clients.py`، `app/device_limit/engine.py`، `app/device_limit/slots.py`، `app/device_limit/constants.py`
- API/model: `app/models/admin.py`، `app/models/device_limit.py`، `app/routers/admin.py`، `app/routers/device_limit.py`، `app/routers/subscription.py`، `app/routers/user.py`
- Xray: `app/xray/config.py`، `app/xray/operations.py`
- health/install: `scripts/healthcheck.py`، `scripts/marzban.sh`، `docker-compose.yml`، `.env.example`
- رابط: `app/dashboard/src/pages/Admins.tsx`، `app/dashboard/src/pages/DeviceLimits.tsx`، `app/dashboard/src/components/UserDeviceLimit.tsx`، `app/dashboard/src/components/UserDialog.tsx` و type/localeهای مرتبط
- آزمون‌ها: `tests/test_device_limit.py`، `tests/test_marzhelp_policy.py`، `tests/test_admin_management.py`، `tests/test_healthcheck.py`، `tests/test_heisenberg_migration.py`، `tests/test_mysql_device_limit_migration.py`

## آزمون‌ها و شواهد

- کل مجموعه برای release `v4.7.0`: `63 passed, 1 skipped, 201 warnings in 45.14s`
- آزمون migration روی SQLite برای سه حالت قدیمی: `3 passed`
- آزمون policy به‌همراه migration: `25 passed, 136 warnings in 11.84s`
- آزمون Device Limit، سیگنال‌های خاموش و مجوز حذف warning: `16 passed, 82 warnings in 14.05s`
- زنجیرهٔ Alembic: `b64e91d7c2a4 -> d7f3a2c9e104 (head)`
- `python -m compileall -q app scripts`: موفق
- TypeScript type-check: موفق، بدون خروجی خطا
- Vite production build: موفق، `1744 modules transformed`
- تولید schema برنامه: موفق، `openapi: ok (57 paths)`
- `graphify update .`: موفق؛ گراف نهایی دارای `4468 nodes`، `9094 edges` و `414 communities` است.
- `git diff --check`: موفق؛ فقط هشدار تبدیل LF/CRLF محیط ویندوز دیده شد.
- `bash -n scripts/marzban.sh` اجرا نشد، چون `bash` روی این ویندوز در دسترس نبود.
- تست MySQL با نام `test_device_limit_migration_recovers_from_mysql_partial_ddl` موجود است، اما چون `TEST_MYSQL_DATABASE_URL` تنظیم نبود، همان یک تست skip شد. هیچ پایگاه زنده یا production تغییر نکرد.

## ریسک عملیاتی باقی‌مانده

- پیش از استقرار production، migration باید روی clone یا staging واقعی MySQL با `TEST_MYSQL_DATABASE_URL` اجرا شود.
- افزودن ستون در جدول‌های بسیار بزرگ می‌تواند در نسخه/تنظیمات خاص MySQL قفل DDL ایجاد کند؛ زمان نگهداری و فضای آزاد باید بررسی شود.
- شاخهٔ محلی نسبت به remote جلو و عقب است؛ ادغام تاریخچه باید جداگانه و با تصمیم کاربر انجام شود.
- هشدارهای تست عمدتاً deprecationهای موجود پروژه‌اند و شکست آزمون نیستند.

## نقطهٔ دقیق ادامه پس از قطع برق

پیاده‌سازی محلی کامل است. ابتدا این فایل و سپس `git status --short` خوانده شود. اگر `Graphify` کامل نشده بود، در ریشهٔ `Marzban` فرمان `graphify update .` فقط یک‌بار اجرا شود. سپس با یک MySQL آزمایشی، `TEST_MYSQL_DATABASE_URL` تنظیم و تست `tests/test_mysql_device_limit_migration.py` اجرا شود. پس از آن تنها کار باقیمانده، بازبینی diff و تصمیم کاربر برای commit/deploy است. در `marzhelp` یا `V2IpLimit` هیچ تغییری انجام نشود.

</div>
