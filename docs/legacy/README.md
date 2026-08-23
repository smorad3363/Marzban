# آرشیو معماری پروژه‌های بازنشسته

این پوشه دانش فنی دو پروژه مستقل را نگه می‌دارد که در تاریخ 2026-08-22 از
workspace حذف شدند. این اسناد جایگزین اجرای آن پروژه‌ها نیستند؛ هدفشان حفظ
معماری، جریان داده، نقاط اتصال، ریسک‌ها و روش بازیابی سورس است.

## پروژه‌ها

| پروژه | آخرین snapshot محلی | شاخه | مخزن بازیابی | وضعیت |
|---|---|---|---|---|
| MarzHelp | `d7af880d96a55fc800b6558008c54c5106f512a5` (`v2`) | `main` | `https://github.com/smorad3363/marzhelp.git` | ربات تلگرام/cron بازنشسته؛ schema و policyهای لازم داخل Marzban مالکیت می‌شوند |
| V2IpLimit | `6d68f169491c820edc1c147c80e883603e5c8318` | `houshmand` | `https://github.com/smorad3363/V2IpLimit.git` | پردازشگر مستقل log و ربات تلگرام بازنشسته؛ device-limit بومی Marzban جایگزین آن است |

جزئیات:

- [مهندسی معکوس MarzHelp](MARZHELP_REVERSE_ENGINEERING.md)
- [مهندسی معکوس V2IpLimit](V2IPLIMIT_REVERSE_ENGINEERING.md)
- [ممیزی فایل‌های Marzban](MARZBAN_FILE_HYGIENE_AUDIT.md)

## Runbook تاریخی

- [MARZBAN_CODEX_MASTER_RUNBOOK_V2_ARCHIVE](MARZBAN_CODEX_MASTER_RUNBOOK_V2_ARCHIVE.md)
  یک snapshot دقیق و فقط تاریخی با SHA256
  `63F4D886F682769CF8964329EFA0ABB16BABB9D826CFA63B61BDB900930B38E5`
  است؛ authoritative نیست و نباید برای اجرای Stageها استفاده شود.
- تنها Runbook اجرایی و authoritative پروژه
  `docs/MARZBAN_CODEX_MASTER_RUNBOOK.md` است.

## مرز عملیاتی

- Marzban در runtime، Docker Compose، requirements یا Git submodule به هیچ‌یک
  از دو مخزن وابسته نیست.
- نام‌های `marzhelp_*` داخل Marzban بقایای بی‌مصرف نیستند. آن‌ها schema سازگاری،
  accounting و policyهای منتقل‌شده به Marzban هستند و نباید بدون migration و
  بررسی کامل حذف یا rename شوند.
- قابلیت device-limit داخل خود Marzban قرار دارد. Telegram wrapper و country
  filtering پروژه V2IpLimit عمداً جزو جایگزین بومی نیستند.
- حذف پوشه‌های مستقل، داده‌های MySQL، migrationهای Marzban یا تنظیمات production
  را حذف نمی‌کند.

## بازیابی سورس قدیمی

در صورت نیاز به بررسی تاریخی، مخزن را بیرون از پوشه Marzban clone و دقیقاً روی
snapshot ثبت‌شده checkout کنید:

```powershell
git clone https://github.com/smorad3363/marzhelp.git
git -C marzhelp checkout d7af880d96a55fc800b6558008c54c5106f512a5

git clone --branch houshmand https://github.com/smorad3363/V2IpLimit.git
git -C V2IpLimit checkout 6d68f169491c820edc1c147c80e883603e5c8318
```

فایل‌های untracked محلی مانند `graphify-out/`، `.codex/`، `AGENTS.md` و اسناد
تحلیلی V2IpLimit در Git آن مخزن‌ها نبودند. دانش لازم از آن‌ها در همین پوشه
خلاصه شده است؛ clone مجدد الزاماً آن فایل‌های محلی را برنمی‌گرداند.
