# یادداشت انتشار v4.9.3

نسخهٔ `v4.9.3` پشتیبانی از آخرین نسخهٔ رسمی MySQL را برای نصب تازه و دیتای موجود
اضافه می‌کند.

- نصب تازه از `mysql:latest` استفاده می‌کند؛ در زمان انتشار این نسخه، مقدار آن
  MySQL `26.7.0` است.
- سازگاری برنامه، migrationهای fresh/legacy/partial-DDL، backup/restore و rollback
  برنامه روی `mysql:8.0` و `mysql:latest` در CI اجرا می‌شوند.
- دستور `marzban mysql-upgrade` دیتای موجود را با مسیر امن
  `8.0 → 8.4 → 9.7 → latest` ارتقا می‌دهد.
- پیش از ارتقا، logical dump و snapshot فیزیکی دیتادایرکتوری همراه checksum ساخته
  می‌شود.
- در هر مرحله سلامت MySQL، نسخهٔ واقعی سرور و در پایان سلامت Marzban بررسی می‌شود.
- تست مستقل CI همان Docker volume را بین تمام نسخه‌ها نگه می‌دارد و حفظ داده را
  کنترل می‌کند.
- خطای GTID در آزمون restore با `--set-gtid-purged=OFF` رفع شده است.

راهنمای اجرا و نکات بازیابی در `docs/MYSQL_LATEST_UPGRADE_FA.md` قرار دارد.
