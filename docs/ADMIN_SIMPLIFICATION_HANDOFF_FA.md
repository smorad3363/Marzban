---
title: تحویل پیاده‌سازی ساده‌سازی مدیر و دسترسی‌های Plan-only
date: 2026-08-25
tags:
  - marzban
  - admin-hierarchy
  - handoff
  - active
status: in-progress
---

# تحویل پیاده‌سازی ساده‌سازی مدیر

> [!important] فرمان ادامه
> در شروع هر جلسه ابتدا این فایل، سپس [[ADMIN_HIERARCHY_ROADMAP_FA#نقطه دقیق ادامه]] و `AGENTS.md` خوانده شود. بعد `git status --short --branch` اجرا و کار از اولین مورد ناتمام بخش «نقطه ادامه» پی گرفته شود.

## درخواست قطعی کاربر

1. نقش `SUPER_ADMIN` از محصول حذف شود؛ فقط `OWNER` و `ADMIN` باقی بمانند. فرم ساخت مدیر گزینه نقش نداشته باشد و هر فرزند جدید `ADMIN` شود.
2. بخش‌های مشخصات، نوع حساب، اجازه ساخت مدیر و روش ساخت کاربر در یک فرم فشرده ادغام شوند.
3. محدودیت‌های اختیاری همیشه باز و در یک ردیف جدا باشند. شناسه تلگرام به این بخش منتقل شود.
4. پلن‌ها و محدودیت دسترسی در یک سطح دائماً باز زیر فرم اصلی باشند؛ نام تولیدشده `css-uf4pty` مستقیم استفاده نشود و ظاهر آن با style پایدار Chakra بازسازی شود.
5. گزینه‌های `prevent_user_creation`، انتخاب `view_full_client_ip` و `prevent_revoke_subscription` از UI حذف شوند. IP کامل برای همه مدیران داخل scope خودشان فعال باشد.
6. Owner برای هر مدیر همیشه «حجم مصرفی کل» و «حجم ساخته‌شده کل» را هم‌زمان ببیند. حذف User یا Reset نباید هیچ‌کدام را کاهش دهد.
7. مدیر `PLAN_ONLY` نتواند `data_limit`، `expire` یا `concurrent_user_limit` را مستقیم ویرایش کند. ساخت و تمدید با Plan مجاز است. Owner از این قفل مستثناست.
8. مدیر `SUSPENDED` بتواند وارد شود، علت فریز و Userهای scope خودش را ببیند، اما هیچ mutation روی User یا پنل انجام ندهد. حساب `DISABLED` محدودتر باقی بماند.
9. پس از پایان پیاده‌سازی، Build واقعی در مرورگر داخلی برای Owner، مدیر Plan-only و مدیر فریز‌شده نمایش داده شود.

## درخواست مالی تأییدشده

- برای modeهای `ALLOCATED_TRAFFIC` و `USER_CREDIT` هر Plan قیمت خرید پولی داشته باشد.
- والد برای فرزند قیمت فروش همان Plan را تعیین کند؛ قیمت فروش نباید از قیمت خرید خود والد کمتر باشد.
- اعتبار مدیر به تومان نگهداری و با ساخت/تمدید از Plan کم شود؛ مدیر بتواند بخشی از اعتبار پولی را به زیرمدیر واگذار کند.
- اختلاف قیمت خرید و فروش، حاشیهٔ سود مدیر میانی است؛ مثال: Owner پلن ۲۰ گیگ را ۵۰ هزار تومان به علی می‌دهد و علی می‌تواند همان Plan را حداقل ۵۰ هزار، مثلاً ۷۰ هزار تومان، به حسین بدهد.
- برای `USED_TRAFFIC` هیچ Plan وجود ندارد؛ ساخت User فقط `FREE_FORM` است. والد قیمت خرید هر GiB فرزند را تعیین می‌کند و فرزند فقط با نرخ مساوی یا بالاتر به زیرمدیر می‌فروشد.
- این بخش با دستور صریح کاربر در حال پیاده‌سازی است؛ انتشار GitHub هنوز مجاز نشده است.

## وضعیت شروع

- branch: `agent/admin-hierarchy-v4.9.0`
- HEAD/tag محلی: `v5.0.0-rc.11@04048b90ce27fd77d0ca3f936faca26da932ef90`
- GitHub Release prerelease تأییدشده: `v5.0.0-rc.11`، زمان `2026-08-25T09:37:04Z`
- GitHub Release پایدار دارای نشان Latest: `v4.9.8`، زمان `2026-08-21T02:16:17Z`
- `git ls-remote` در شروع به‌علت `Could not resolve host: github.com` ناموفق بود.
- GHCR digest به‌علت پاسخ `403` و نبود scope `read:packages` قابل تأیید نبود. هر کار release-sensitive تا تأیید دوباره متوقف است.
- working tree از قبل تغییرات مرتبط با اصلاح `PLAN_ONLY` و Modal دارد. فایل‌های حذف‌شده و untracked متعلق به کاربرند و نباید حذف یا revert شوند.

## شواهد ریشه مشکل

- `AdminFormDrawer.tsx` چهار Section اصلی و سه Accordion جدا دارد؛ گزینه role و تنظیمات پیشرفته هنوز نمایش داده می‌شوند.
- `add_user()` مسیر ساخت خام را برای `PLAN_ONLY` می‌بندد، ولی `validate_update()` و `PUT /api/user/{username}` تغییر مستقیم حجم، زمان و تعداد دستگاه را هنوز می‌پذیرند.
- `Admin.get_current()` برای حساب غیر Active فقط چهار path ثابت را مجاز می‌کند؛ `/api/users` داخل آن نیست، پس مدیر فریز‌شده Userها را نمی‌بیند.
- `MarzhelpDeletedUser` و `MarzhelpAccountingTransaction` سابقه حذف و حسابداری را نگه می‌دارند. مصرف واقعی حذف‌شده اکنون در `quota_summaries()` لحاظ می‌شود؛ API/UI باید دو شاخص تاریخی مستقل را هم‌زمان نمایش دهند.

## تصمیم‌های فنی

- lookup قدیمی `SUPER_ADMIN` در DB حذف فیزیکی نشود تا rollback امن بماند. در runtime همهٔ رکوردهای قدیمی `SUPER_ADMIN` به‌صورت `ADMIN` نمایش و ارزیابی شوند؛ اجرای `set-owner` نیز همهٔ رکوردهای غیر Owner را به `ADMIN` تبدیل کند. این راه بدون migration و برگشت‌پذیر است.
- آمار تاریخی با موجودی اعتبار مخلوط نشود. حذف یا refund می‌تواند موجودی را تغییر دهد، اما شاخص lifetime هرگز کم نشود.
- قفل Plan-only هم در UI و هم در Backend اعمال شود؛ پنهان‌کردن field بدون authorization سرور کافی نیست.
- برای `SUSPENDED` فقط methodهای `GET/HEAD/OPTIONS` مجاز باشند و routeهای موجود همچنان scope را کنترل کنند. `DISABLED` allowlist محدود فعلی را نگه دارد.
- UI با React 18 و Chakra 2 موجود پیاده شود؛ dependency جدید ممنوع.

## نقطه ادامه

- [x] مدل کیف پول تومان، قیمت immutable نسخه Plan، قیمت واگذارشده و دفتر پول طراحی و اضافه شد.
- [x] migration بعد از `8b7d3e5f1a24` اضافه شد؛ حساب‌های مهاجرتی به‌طور امن با billing پولی خاموش شروع می‌شوند.
- [x] واگذاری/پس‌گیری پول direct-child و زنجیره سود Plan با idempotency پیاده شد.
- [x] تسویه مصرف واقعی با دقت کسری GiB و سود چندسطحی در همان transaction ثبت usage پیاده شد.
- [x] backend modeها را اجباری می‌کند: `USED_TRAFFIC=FREE_FORM/no Plan` و `ALLOCATED_TRAFFIC|USER_CREDIT=PLAN_ONLY`.
- [x] UI اولیه قیمت Plan، قیمت هر GiB، اعتبار تومان و قیمت فروش فرزند اضافه شد.
- [x] رفع خطاهای syntax/type و تکمیل تست‌های هدفمند مالی.
- [x] اجرای migration contract، تست نهایی Backend، TypeScript، قرارداد UI و Build.
- [x] `graphify update .`، fixture پیش‌نمایش و بررسی مرورگر داخلی.

- [x] تحلیل source، Graphify، MySQL و SQL انجام شد.
- [x] baseline و محدودیت انتشار ثبت شد.
- [x] نقش محصول به `OWNER` و `ADMIN` محدود شد؛ ساخت فرزند فقط `ADMIN` است و گزینه/فیلتر نقش از UI حذف شد.
- [x] lookup قدیمی `SUPER_ADMIN` فقط برای سازگاری DB نگه داشته شد؛ migration جدید لازم نیست.
- [x] Backend lifetime metrics، Plan-only و suspended read-only اصلاح شد.
- [x] فرم مدیر و صفحه فهرست مدیران اصلاح شدند.
- [x] UI کاربران برای Plan-only و suspended read-only اصلاح شد.
- [x] targeted tests، قرارداد UI، TypeScript و Vite اجرا شد.
- [x] `graphify update .` اجرا شد.
- [x] Build در مرورگر داخلی بررسی شد و پیش‌نمایش باز ماند.

## آخرین نتیجهٔ قابل اتکا

- قیمت پولی Plan، کیف پول تومان، نرخ هر GiB، margin چندسطحی، transfer مستقیم والد/فرزند و ledger پیاده شد.
- تسویه `USED_TRAFFIC` در همان transaction ثبت usage انجام می‌شود؛ کسری GiB گم نمی‌شود و ledger مصرف برای کنترل رشد جدول در bucket ساعتی تجمیع می‌شود.
- migration جدید: `c2f4a8d6e913` بعد از `8b7d3e5f1a24`. حساب‌های قدیمی با `money_billing_enabled=0` مهاجرت می‌شوند؛ با نخستین ذخیره تنظیم تجاری جدید فعال می‌شوند.
- Backend هدفمند نهایی: `69 passed` از پنج suite مجاور + تست اصلاح‌شده اولیه پولی + `3 passed` تست زنجیره مالی + `2 passed` قرارداد migration. یک failure قدیمی resource-ledger مطابق مدل پولی جدید بازنویسی و PASS شد.
- Frontend: Admin UX=`PASS`، hierarchy authorization=`PASS`، Plan/Inbound=`14 assertions`، TypeScript=`PASS`، Vite=`1773 modules`.
- Browser داخلی: `http://127.0.0.1:8000/dashboard/#/admins/` با `owner / Preview@1405`؛ Modal ساخت مدیر روی «حجم ساخته‌شده» باز است و قیمت خرید/فروش سه Plan را نشان می‌دهد.
- Graphify=`4538 nodes / 11708 edges / 485 communities`.
- MySQL زنده در این مرحله در دسترس نبود؛ schema فقط additive است، اما اجرای migration واقعی MySQL/CI پیش از انتشار لازم است.
- push، tag، release و deploy انجام نشده؛ نیازمند دستور صریح کاربر است.

- کد هر چهار درخواست تکمیل شد؛ push، tag، release و deploy هنوز انجام نشده است.
- Backend هدفمند: `61 passed` در hierarchy، Plan-only، lifetime/delete/reset/renew و ledger.
- Frontend: Admin UX=`PASS`، hierarchy authorization=`PASS`، Plan/Inbound=`14 assertions`، TypeScript=`PASS`، Vite production build=`1773 modules`.
- Browser داخلی: `http://127.0.0.1:8000/dashboard/#/admins/` با fixture محلی Owner باز است؛ Modal فشردهٔ ساخت مدیر باز و Console همان tab برابر `0 error` است.
- آمار lifetime با سه query گروهی موجود محاسبه می‌شود؛ query جدید N+1 اضافه نشد. counter موجود `provisioning_volume_used` برای ساخت‌های بعدی monotonic شد و حذف/reset آن را کم نمی‌کند؛ migration جدید لازم نیست.
- MySQL زنده در زمان preview در دسترس نبود؛ تست‌های هدفمند با fixtureهای SQLite گذشتند. ریسک عملیاتی schema ندارد، ولی CI MySQL هنگام انتشار باید گیت نهایی باشد.
- Graphify=`4505 nodes / 11552 edges / 492 communities`.
- نقطهٔ بعدی: فقط در صورت دستور صریح کاربر، review manifest و انتشار immutable بعدی.

## اصلاح نهایی قیمت پلن و پیش‌نمایش

- [x] قیمت Plan فقط در ساخت/نسخهٔ جدید خود Plan تنظیم می‌شود.
- [x] انتخاب دسته/نوع Plan و قیمت فروش Plan از فرم ساخت/ویرایش Admin حذف شد.
- [x] Adminهای پولی `ALLOCATED_TRAFFIC` و `USER_CREDIT` همهٔ Planهای فعال را با قیمت ثابت نسخهٔ Plan می‌بینند؛ `USED_TRAFFIC` همچنان Plan ندارد و با قیمت هر GiB کار می‌کند.
- [x] API ساخت/ویرایش Admin دیگر دسته یا قیمت اختصاصی Plan را واگذار نمی‌کند؛ جدول‌های قدیمی برای rollback و سازگاری حذف نشده‌اند.
- [x] تست مالی هدفمند، قرارداد UI، TypeScript و Build (`1773 modules`) پاس شد.
- [x] پیش‌نمایش محلی با تزریق token خودکار بازبینی شد؛ ورود دستی لازم نیست.

## فایل‌های محتمل

- `app/utils/admin_hierarchy.py`
- `app/utils/marzhelp_policy.py`
- `app/models/admin.py`
- `app/routers/admin.py`
- `app/routers/user.py`
- `app/db/models.py`
- `app/db/migrations/versions/`
- `app/dashboard/src/components/AdminFormDrawer.tsx`
- `app/dashboard/src/pages/Admins.tsx`
- `app/dashboard/src/components/UserDialog.tsx`
- `app/dashboard/src/components/UsersTable.tsx`
- `app/dashboard/src/components/Filters.tsx`
- `app/dashboard/src/types/Admin.ts`
- `tests/` و `app/dashboard/scripts/test-admin-ux.cjs`

## اجرای تک‌دستوری محیط Dev محلی

- لانچر: `scripts/dev-local.ps1`
- seed تکرارپذیر: `scripts/dev_seed.py`
- DB فقط `marzban_dev` روی پورت `33079` است؛ guard هر URL دیگر را رد می‌کند.
- Docker یک MySQL 8.0 آزمایشی و Backend واقعی همراه Xray می‌سازد؛ Backend روی `8000`
  با reload و Vite روی `3000` با HMR اجرا می‌شوند.
- Owner: `owner / DevOwner@1405`
- Adminها: `plan_admin`, `usage_admin`, `frozen_admin` با رمز `DevAdmin@1405`
- اجرای واقعی integration در `2026-08-26` ممکن نبود، چون Docker Desktop روی Windows
  نصب نبود. PowerShell parser، Python compile/import و DB safety guard پاس شدند.

## یادداشت مقیاس و DB

> [!warning]
> آمار فهرست مدیران نباید N+1 ایجاد کند. queryهای lifetime برای Adminهای همان صفحه باید grouped باشند یا از counterهای transaction-safe استفاده کنند. هر migration روی MySQL 8.x باید rerunnable و rollback-compatible باشد.
