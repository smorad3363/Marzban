# مهندسی معکوس MarzHelp

تاریخ snapshot: 2026-08-22

## هویت snapshot

- مسیر حذف‌شده: `C:\Users\Saji\Desktop\vProject\marzhelp`
- remote: `https://github.com/smorad3363/marzhelp.git`
- branch: `main`
- commit: `d7af880d96a55fc800b6558008c54c5106f512a5`
- tag/describe: `v2`
- حجم مشاهده‌شده: 195 فایل و 3,677,465 بایت
- موارد untracked هنگام بازنشستگی: `.codex/`، `AGENTS.md` و `graphify-out/`

## هدف و وضعیت نهایی

MarzHelp یک companion مستقل PHP برای Marzban بود. رابط اصلی آن ربات تلگرام،
پردازش webhook، cron و مدیریت محدودشده admin/user بود. این پروژه از Marzban API
و schema مشترک MySQL استفاده می‌کرد.

در معماری فعلی:

- Marzban v4 تنها مالک ایجاد و migration جدول‌های `marzhelp_*` است.
- policyهای create/renew/edit/activate/transfer/delete کاربر داخل transactionهای
  Marzban و `app/utils/marzhelp_policy.py` enforce می‌شوند.
- MarzHelp فقط یک consumer رابط تلگرام/cron بود و برای runtime فعلی Marzban لازم
  نیست.
- trigger/eventهای قدیمی `marzhelp_admin_enforcement` دیگر مبنای enforcement
  نیستند؛ نتیجه‌گیری‌های تاریخی مبتنی بر آن‌ها منسوخ‌اند.

## ساختار مؤلفه‌ها

```text
marzhelp/
├── webhook.php                  ورودی HTTPS وبهوک تلگرام
├── bot.php                      state machine پیام‌ها و callbackها
├── crons/cron.php               sync، quota، expiry، traffic و اعلان‌ها
├── app/
│   ├── bootstrap.php            bootstrap برنامه
│   ├── security.php             اعتبارسنجی webhook و مجوز admin
│   ├── scrub_config.php         پاک‌سازی/اعتبارسنجی config
│   ├── classes/marzban.php      کلاینت HTTP برای Marzban API
│   ├── functions/               keyboard و pagination
│   └── languages/               ترجمه‌های en/fa/ru
├── config.php.example           قرارداد تنظیمات
├── install.sh                   نصب PHP/web server/webhook/cron/DB accounts
├── update.sh                    update و backup
├── bootstrap.sh                 bootstrap shell
├── table.php                    عملیات/نمایش جدولی
└── tests/                       تست‌های پروژه
```

## جریان runtime

```text
Telegram
  -> webhook.php
     -> validateWebhookSecret()
     -> تشخیص message یا callback_query
     -> bot.php::handleMessage()/handleCallbackQuery()
        -> بررسی Telegram admin و محدودیت‌های admin
        -> Marzban HTTP API
        -> canonical Marzban MySQL برای state و گزارش

cron
  -> crons/cron.php
     -> Database / Notification / PanelManager
     -> sync پنل و inbound
     -> بررسی quota، expiry و traffic
     -> اعلان تلگرام و update داده‌های runtime
```

## نقاط ورود

### `webhook.php`

- هدرهای request را استخراج می‌کرد.
- secret وبهوک را با تنظیمات تطبیق می‌داد.
- payload تلگرام را parse و به handler مناسب هدایت می‌کرد.

### `bot.php`

- مکالمه تلگرام را به‌صورت state machine اجرا می‌کرد.
- عملیات user/admin، pagination، keyboard و callbackها را مدیریت می‌کرد.
- عملیات پنل را از طریق `app/classes/marzban.php` انجام می‌داد.
- authorization را با `app/security.php` و policyهای admin محدود می‌کرد.

### `crons/cron.php`

- کلاس‌های اصلی `Database`، `Notification` و `PanelManager` را داشت.
- sync دوره‌ای، اعلان، quota، expiry، traffic و برخی کارهای نگهداری را انجام
  می‌داد.

## قرارداد تنظیمات

نام کلیدها برای بازیابی قرارداد ثبت شده‌اند؛ هیچ secret یا مقدار production در
این سند ذخیره نشده است.

```php
$botToken
$apiURL
$botdomain
$webhookSecret
$allowSystemCommands
$storagePath
$allowedUsers
$botDbHost
$botDbUser
$botDbPass
$botDbName
$vpnDbHost
$vpnDbUser
$vpnDbPass
$vpnDbName
$migrationDbUser
$migrationDbPass
$marzbanUrl
$marzbanAdminUsername
$marzbanAdminPassword
```

- database canonical: `marzban`
- runtime DB account پیش‌فرض: `marzhelp_app`
- migration DB account پیش‌فرض: `marzhelp_migrate`

## سطح Marzban API مصرف‌شده

کلاینت `app/classes/marzban.php` این خانواده عملیات را پوشش می‌داد:

- دریافت token از `/api/admin/token`
- list/create/update/delete admin
- disable/activate admin و reset usage
- core config/status/restart
- list/create/update/delete/reconnect node و node usage
- system statistics، inbounds و hosts
- template CRUD
- user CRUD، reset/revoke usage، activate-next، set-owner و expired users

این API surface یک snapshot تاریخی است؛ برای پیاده‌سازی جدید باید قرارداد API
نسخه جاری Marzban دوباره بررسی شود.

## مالکیت داده و schema

MarzHelp مستقیماً DML انجام می‌داد، اما در معماری نهایی مالک DDL نبود. migration
`9f4a1c2d7e31` در Marzban جدول‌های canonical را ایجاد می‌کند.

### جدول‌های اصلی Marzban که مصرف می‌شدند

- `admins`
- `users`
- `user_usage_logs`
- `inbounds`
- `proxies`
- `exclude_inbounds_association`

### جدول‌های compatibility و policy

- `marzhelp_metadata`
- `marzhelp_admin_settings`
- `marzhelp_admin_allowed_inbounds`
- `marzhelp_admin_allowed_user_limits`
- `marzhelp_admin_allowed_subscription_modes`
- `marzhelp_user_states`
- `marzhelp_user_temporaries`
- `marzhelp_admin_usage`
- `marzhelp_limits`
- `marzhelp_runtime_settings`
- `marzhelp_deleted_users`
- `marzhelp_accounting_transactions`

### مسیر migration مرتبط در Marzban

```text
63fbd07b9f14
  -> 9f4a1c2d7e31  canonical MarzHelp schema
  -> c8e2a4f6b901  admin user count
  -> ...
  -> f42c0e8a7d31  admin inbound and weighted limits
  -> b64e91d7c2a4  native device limits
  -> d7f3a2c9e104  Heisenberg capabilities and quotas
  -> a41c8e7d5b92  unified admin credit/allowance
  -> e2a6c1f4b903  hierarchy foundation
```

قبل از حذف یا rename هر جدول `marzhelp_*` باید همه migrationها، modelها، queryها،
backup/restore و مسیرهای CRUD بررسی شوند. نام legacy به‌تنهایی دلیل اضافی بودن
جدول نیست.

## نصب و عملیات قدیمی

`install.sh` برای این موارد طراحی شده بود:

- نصب PHP و وب‌سرور با ملاحظات coexistence برای Nginx/Apache
- TLS و webhook روی port 88
- ایجاد cron
- ایجاد MySQL accountهای محدود runtime/migration
- نصب برنامه در `/var/www/html/marzhelp`
- backup در `/var/backups/marzhelp`

در معماری فعلی نباید این installer روی سرور Marzban اجرا شود. backup استاندارد
database و فایل‌های Marzban برای schema منتقل‌شده مرجع است.

## مدل امنیت و ریسک‌های تاریخی

- secretهای bot، database و Marzban admin در config محلی قرار می‌گرفتند.
- webhook secret اولین مرز اعتبارسنجی request بود.
- Telegram admin ID و limited-admin policy لایه مجوز بعدی بودند.
- قابلیت اجرای system command وجود داشت و با `$allowSystemCommands` کنترل می‌شد.
- برنامه DML مستقیم روی database مشترک انجام می‌داد؛ ناسازگاری نسخه خطرناک بود.
- template/URLهای خارجی و credentialهای admin سطح حمله را افزایش می‌دادند.
- backup یا config قدیمی نباید بدون scrub در repository یا سند قرار گیرد.

## جایگزین داخل Marzban

| قابلیت قدیمی | مالک فعلی |
|---|---|
| schema و migration | migrationهای Alembic خود Marzban |
| enforcement policy admin/user | `app/utils/marzhelp_policy.py` و CRUDهای Marzban |
| quota/allowance/accounting | modelها و transactionهای canonical Marzban |
| hierarchy و capability | مدل‌ها/API/dashboard پروژه Heisenberg |
| Telegram bot و cron اختصاصی | بازنشسته؛ جایگزین runtime لازم نیست |

## نتیجه بازنشستگی

پوشه مستقل MarzHelp برای build، نصب، migration یا اجرای Marzban لازم نیست. آنچه
باید حفظ شود schema و policyهای داخلی Marzban است، نه executable ربات تلگرام.
در صورت نیاز به تحقیق تاریخی، snapshot ثبت‌شده در ابتدای سند قابل clone است.
