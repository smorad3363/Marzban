# ممیزی read-only فایل‌های Marzban

تاریخ ممیزی: 2026-08-22

این گزارش فقط پیشنهاد cleanup است. در این ممیزی هیچ فایل موجودی داخل Marzban
حذف، جابه‌جا یا reset نشده است. تنها فایل‌های جدید همین پوشه `docs/legacy/` هستند.

## نتیجه کوتاه

dependency اجرایی به MarzHelp یا V2IpLimit یافت نشد. چند دسته artifact محلی و
cache قابل پاک‌سازی هستند، اما بعضی مسیرها حاوی تغییرات فعال Stage 4 تا 6 یا حافظه
ابزار هستند و حذف کورکورانه آن‌ها خطرناک است.

## اندازه artifactهای محلی مشاهده‌شده

| مسیر | تعداد فایل | حجم تقریبی | ارزیابی |
|---|---:|---:|---|
| `.codex/` | 3,761 | 353.07 MiB | local tooling/browser data؛ بالقوه حساس |
| `graphify-out/` | 832 | 80.16 MiB | knowledge graph؛ قابل بازسازی ولی ممکن است حافظه مفید داشته باشد |
| `.venv/` | 8,054 | 116.45 MiB | محیط مجازی قابل بازسازی |
| `.venv-heisenberg/` | 5,861 | 88.49 MiB | محیط مجازی قابل بازسازی |
| `app/dashboard/node_modules/` | 23,762 | 251.91 MiB | dependency قابل بازسازی |
| `app/dashboard/dist/` | 23 | 8.27 MiB | build output؛ وضعیت release باید بررسی شود |
| `design-system/` | 2 | 0.01 MiB | هدف نامشخص؛ پیش از حذف بررسی شود |

همچنین cacheهای Python/test، `db.sqlite3` و فایل‌های
`migration-v460-check*.sqlite3` مشاهده شدند. این SQLiteها ignored و untracked
هستند و ظاهراً artifact تست/migration محلی‌اند، اما قبل از حذف باید اطمینان حاصل
شود داده مرجع یا fixture دستی داخلشان نیست.

## گزینه‌های cleanup کم‌ریسک برای اجرای بعدی

این موارد معمولاً قابل بازسازی‌اند؛ حذف فقط با تأیید جداگانه انجام شود:

- `.venv/` و `.venv-heisenberg/`
- `app/dashboard/node_modules/`
- `.pytest_cache/`، `.ruff_cache/` و `__pycache__/`
- SQLiteهای تستی `migration-v460-check*.sqlite3`
- `db.sqlite3` فقط اگر محیط فعال از SQLite استفاده نمی‌کند
- artifactهای موقت `.codex/tmp` و browser/runtime cacheهای `.codex/`
- پوشه‌های تست موقت `.test-*` پس از رفع/بررسی ACL
- snapshotها و logهای قدیمی `graphify-out/` پس از export یا rebuild موفق

## مواردی که نباید به‌عنوان junk حذف شوند

- `app/utils/marzhelp_policy.py` و model/tableهای `marzhelp_*`
- `app/device_limit/`، routerها، migrationها و dashboard device-limit
- `xray_config.json`؛ این فایل tracked است
- `marzban.code-workspace`؛ این فایل tracked است
- assetهای hashدار قدیمی/جدید dashboard تا زمانی که build و packaging release
  تعیین نکرده کدام مجموعه مرجع است
- `graphify-out/` بدون تصمیم درباره حفظ حافظه و re-index
- `design-system/` تا تعیین مالکیت و کاربرد
- هر فایل modified/deleted فعلی در Git؛ این‌ها تغییرات فعال کاربر/Stageها هستند

## وضعیت working tree

هنگام ممیزی، Marzban clean نبود. تغییرات فعال در dashboard، device-limit،
`marzhelp_policy.py`، تست‌ها و docs دیده شد. assetهای build جدید، scriptها و فایل
plan نیز untracked بودند. این وضعیت cleanup خودکار با `git clean` را ناامن می‌کند.

هشدارهای permission برای این مسیرهای تست مشاهده شد:

```text
.test-all-v460
.test-device-limit
.test-device-limit-2
.test-device-limit-current
.test-final-v460
.test-suite-current
```

این پوشه‌ها ابتدا باید با ACL و مالکیت درست inspect شوند؛ دستور recursive delete
کورکورانه مناسب نیست.

## ریسک Docker build context

`Dockerfile` از `COPY . /code` استفاده می‌کند. `.dockerignore` فعلی مواردی مانند
`node_modules`، `.venv`، `db.sqlite3`، Git و فایل‌های Markdown را کنار می‌گذارد،
اما این مسیرها را به‌صورت عمومی exclude نمی‌کند:

- `.codex/`
- `graphify-out/`
- `design-system/`
- `.pytest_cache/`
- `.ruff_cache/`
- `migration-*.sqlite3`

در build از checkout تمیز Git، untrackedها وجود ندارند؛ ولی build مستقیم از
workspace محلی ممکن است آن‌ها را وارد context کند، زمان build را بالا ببرد یا
داده محلی/حساس را در معرض daemon قرار دهد. پیشنهاد بعدی افزودن ignoreهای دقیق پس
از بررسی نیاز packaging است.

## پیشنهاد ترتیب cleanup آینده

1. ابتدا تغییرات فعال را commit/stash یا دقیقاً دسته‌بندی کنید.
2. با `git status --short` و `git clean -nd` فقط dry-run بگیرید.
3. `.codex/` و `graphify-out/` را جدا از artifactهای build تصمیم‌گیری کنید.
4. venv، node_modules و cacheها را از lockfileها بازسازی‌پذیر تأیید کنید.
5. dashboard را با build استاندارد تولید و فقط assetهای obsolete را بر اساس
   manifest حذف کنید.
6. بعد از حذف ساختاری، Graphify را rebuild/re-index و با `rg` و Git تطبیق دهید.
7. migration و تست‌های backend/frontend/device-limit را دوباره اجرا کنید.

در این مرحله هیچ‌یک از پیشنهادهای بالا اجرا نشده است.
