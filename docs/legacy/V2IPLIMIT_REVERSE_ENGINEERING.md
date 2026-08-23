# مهندسی معکوس V2IpLimit

تاریخ snapshot: 2026-08-22

## هویت snapshot

- مسیر حذف‌شده: `C:\Users\Saji\Desktop\vProject\V2IpLimit`
- remote: `https://github.com/smorad3363/V2IpLimit.git`
- branch: `houshmand`
- commit: `6d68f169491c820edc1c147c80e883603e5c8318`
- describe: `6d68f16`
- حجم مشاهده‌شده: 142 فایل و 7,321,473 بایت
- موارد untracked هنگام بازنشستگی: `AGENTS.md`، `docs/` و `graphify-out/`

## هدف و وضعیت نهایی

V2IpLimit یک پردازشگر مستقل async بود که access logهای Xray را از master و node
می‌گرفت، IPهای فعال هر user را تخمین می‌زد و user متخلف را از طریق Marzban API
غیرفعال می‌کرد. یک Telegram bot برای config و عملیات نیز همراه آن بود.

Marzban فعلی device-limit را به‌صورت بومی در backend، job، database، API و
dashboard خود پیاده می‌کند. بنابراین binary/process، Telegram bot و state fileهای
V2IpLimit برای runtime Marzban لازم نیستند.

## ساختار مؤلفه‌ها

```text
V2IpLimit/
├── v2iplimit.py                 orchestration و loop اصلی async
├── run_telegram.py              اجرای bot تنظیمات/مدیریت
├── telegram_bot/                handlerها، commandها و config bot
├── utils/                       API client، log parser، state و helpers
├── v2iplimit.sh                 launcher/install/update مبتنی بر screen
├── core_test.py                 تست دستی و بالقوه مخرب
├── requirements.txt             dependencyهای runtime Python
├── build_requirements.txt       dependencyهای build
└── .github/                     workflowها و Dependabot
```

## جریان runtime

```text
v2iplimit.py::main()
  -> شروع Telegram polling
  -> انتظار برای config معتبر
  -> ساخت PanelType و token/API context
  -> تلاش برای فعال‌سازی userهای ذخیره‌شده از اجرای قبل
  -> دریافت nodeها
  -> ایجاد collector برای master و هر node
     -> WebSocket log stream
     -> parse accepted Xray access logs
     -> نگاشت email/user و IP عمومی
  -> loop دوره‌ای
     -> کشف/حذف node taskها
     -> check_users_usage()
     -> disable_user() برای تخلف
     -> enable_selected_users() پس از timeout
  -> restart loop پس از خطای کنترل‌نشده
```

## endpointهای مصرف‌شده

### Marzban HTTP API

- `POST /api/admin/token`
- `GET /api/users`
- `PUT /api/user/{username}`
- `GET /api/nodes`

### Xray/Marzban log stream

- `/api/core/logs?interval=...&token=...`
- `/api/node/{id}/logs?interval=...&token=...`

پروژه database مستقیم یا Xray API مستقیم نداشت؛ کنترل user از طریق Marzban API
و مشاهده اتصال‌ها از طریق WebSocket log انجام می‌شد.

## الگوریتم تشخیص

1. فقط logهای accepted مربوط به access پردازش می‌شدند.
2. IP عمومی و email/user از log استخراج می‌شد.
3. prefix عددی username در برخی قالب‌ها حذف می‌شد.
4. IP بعد از حداقل سه مشاهده accepted وارد شمارش می‌شد.
5. حد مجاز از `GENERAL_LIMIT` یا `SPECIAL_LIMIT` می‌آمد؛ `EXCEPT_USERS` مستثنا بود.
6. شرط تخلف strict بود: تعداد IP باید از limit بیشتر می‌شد.
7. user با status `disabled` از طریق Marzban API غیرفعال می‌شد.
8. اطلاعات disable در `.disable_users.json` نگه‌داری و پس از timeout یا startup
   برای re-enable استفاده می‌شد.

این الگوریتم تعداد socket هم‌زمان واقعی را اندازه نمی‌گرفت؛ فراوانی IP در log را
به‌عنوان تقریب activity استفاده می‌کرد.

## قرارداد تنظیمات

هیچ token، password، domain یا مقدار production در این سند ذخیره نشده است.

### الزامی برای Telegram/config bootstrap

- `BOT_TOKEN`
- `ADMINS`

### الزامی برای loop اصلی

- `PANEL_DOMAIN`
- `PANEL_USERNAME`
- `PANEL_PASSWORD`
- `CHECK_INTERVAL`
- `TIME_TO_ACTIVE_USERS`
- `IP_LOCATION`
- `GENERAL_LIMIT`

### اختیاری

- `SPECIAL_LIMIT`
- `EXCEPT_USERS`

## state و فایل‌های runtime

- `config.json`: config و credentialهای runtime
- `.disable_users.json`: userهای غیرفعال‌شده و زمان‌بندی re-enable
- `app.log`: log چرخشی برنامه
- حافظه process: IP activity، cacheها، node taskها و user state

## dependency و launcher

`requirements.txt` دقیقاً شامل این dependencyهای runtime بود:

```text
websockets==15.0
python-telegram-bot==21.10
```

`v2iplimit.sh` از `screen`، `wget` و `jq` استفاده می‌کرد و artifact نسخه `1.0.6`
را از releaseهای `houshmand-2005/V2IpLimit` دریافت می‌کرد. این launcher دیگر
نباید جزئی از نصب Marzban باشد.

## سرویس‌های country lookup

بر اساس `IP_LOCATION` یکی از endpointهای خارجی زیر قابل استفاده بود:

- `http://ip-api.com/json/`
- `https://ipinfo.io/`
- `https://api.iplocation.net/?ip=`
- `https://ipapi.co/`

country filtering در device-limit بومی Marzban port نشده است و با تصمیم فعلی
نیاز نیست.

## ریسک‌ها و رفتارهای تاریخی

- Telegram polling در مسیر import/config خیلی زود شروع می‌شد.
- اگر `ADMINS` خالی بود، اولین chat می‌توانست admin اولیه شود.
- command مربوط به backup می‌توانست کل `config.json` را ارسال کند.
- در برخی درخواست‌های panel/country بررسی TLS غیرفعال بود.
- failure سرویس country به‌شکل fail-open رفتار می‌کرد.
- state در بعضی failureها زود پاک می‌شد.
- startup re-enable می‌توانست فایل state را پیش از موفقیت عملیات خالی کند.
- outer loop پس از exception گسترده restart می‌شد و علت اصلی را پنهان می‌کرد.
- تغییر status تضمین نمی‌کرد connection موجود همان لحظه قطع شود.
- `core_test.py` تست دستی بالقوه مخرب بود و نباید در production اجرا شود.

## جایگزین بومی داخل Marzban

| قابلیت V2IpLimit | جایگزین Marzban |
|---|---|
| master/node log collectors | `app/device_limit/engine.py` |
| schedule و lifecycle | `app/jobs/device_limit.py` |
| API مدیریت | `app/routers/device_limit.py` |
| ثبت router | `app/routers/__init__.py` |
| UI | `app/dashboard/src/pages/DeviceLimits.tsx` و `UserDeviceLimit.tsx` |
| state ماندگار | جدول‌های MySQL device-limit |
| limit هر user | `concurrent_user_limit` و تنظیمات/penaltyهای بومی |
| Telegram config wrapper | بازنشسته و غیرضروری |
| country filtering خارجی | عمداً port نشده است |

### جدول‌های native device-limit

- `device_limit_settings`
- `device_limit_penalty_stages`
- `device_slots`
- `device_client_observations`
- `device_limit_user_states`
- `device_limit_incidents`

نکات طراحی database:

- slot روی `(user_id, slot_index)` unique است.
- observation روی `(user_id, slot_key, normalized_identity)` unique است.
- indexهای user/seen، slot، penalty/until و incident audit برای queryهای دوره‌ای
  وجود دارند.
- state، incident، retention و audit در MySQL نگه‌داری می‌شوند؛ فایل JSON مرجع
  عملیاتی نیست.

## محدودیت اعتبارسنجی

بررسی سورس و تست‌های محلی انجام شده، اما اثبات end-to-end واقعی traffic بین
master، node و tunnel در محیط production در snapshot این سند اجرا نشده بود.
قبل از rollout حساس باید این سناریو با traffic واقعی، reconnect، restart و
accounting آزمایش شود.

## نتیجه بازنشستگی

Marzban هیچ import، submodule، requirement یا service وابسته به V2IpLimit ندارد.
قابلیت اصلی آن در Marzban بومی شده و Telegram/country wrapper طبق نیاز فعلی کنار
گذاشته شده است. برای مطالعه تاریخی می‌توان commit ثبت‌شده را دوباره clone کرد.
