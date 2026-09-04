# نقشه راه Owner، Super Admin، Admin، سلسله‌مراتب و انتقال اعتبار

آخرین به‌روزرسانی: `2026-09-04`

وضعیت: `V5.1.0_RELEASE_IN_PROGRESS` — پیاده‌سازی و gate محلی کامل است؛ commit، tag، CI، GHCR و تست نصب/آپدیت انتشار در حال انجام است.

## قانون اجباری شروع هر چت و هر جلسه

این بخش همراه با `AGENTS.md` مرجع دائمی پروژه است و در همین چت، چت‌های بعدی و ادامه پس از قطع برق باید پیش از هر تغییر خوانده شود.

1. ابتدا این فایل، «نقطه دقیق ادامه» و آخرین ردیف «لاگ پیشرفت» خوانده شود.
2. سپس وضعیت Git، branch، HEAD، remote، tagها و تغییرات ذخیره‌نشده بررسی شود.
3. آخرین نسخه هرگز از حافظه یا حدس انتخاب نشود. این چهار مقدار جداگانه از GitHub/Git/GHCR تأیید و در لاگ ثبت شوند:
   - جدیدترین tag تغییرناپذیر قابل‌نصب.
   - commit دقیق همان tag.
   - GitHub Release دارای نشان `Latest`.
   - tag و digest تغییرناپذیر image در GHCR.
4. tag نصب فعلی و tag قابل rollback نیز ثبت شوند.
5. اگر شبکه یا GitHub در دسترس نبود، خطا ثبت شود و کار وابسته به release متوقف بماند؛ نسخه حدسی استفاده نشود.
6. پیش از هر تغییر معنادار، «نقطه دقیق ادامه» به‌روزرسانی و پس از آن ردیف لاگ کامل اضافه شود.

### baseline تأییدشده در `2026-08-18`

- remote: `https://github.com/smorad3363/Marzban.git`
- جدیدترین Git tag قابل‌نصب: `v4.8.0`
- commit tag: `fd73e03d3dffff158f3354883224f5a4094de2d7`
- tag قبلی: `v4.7.1`
- commit قبلی: `447d9265bd3738883709042f85e5acd30509a827`
- GitHub Release دارای نشان `Latest` در زمان بررسی: `v4.3.0`
- نتیجه: برای نصب و توسعه بعدی، baseline فعلی `v4.8.0` است؛ صفحه Release از tagهای نصب عقب‌تر است.

### baseline بازتأییدشده در شروع پیاده‌سازی `2026-08-18`

- branch و HEAD محلی: `agent/heisenberg-v4.8.0@fd73e03d3dffff158f3354883224f5a4094de2d7`
- remote tag: شیء annotated برابر `466f4148dfe2f5c124618f62a57c1af53318f95d` و commit نهایی tag برابر `fd73e03d3dffff158f3354883224f5a4094de2d7`
- GitHub Release دارای نشان `Latest`: `v4.8.0`، منتشرشده در `2026-08-18T00:36:33Z`
- image نصب: `ghcr.io/smorad3363/marzban:v4.8.0`
- digest تغییرناپذیر image: `sha256:374b0e18d4daa289d99692256f3fb264ddd93eca9a1f752837d6d7a17e1ed9b8`
- tag rollback: `v4.7.1@447d9265bd3738883709042f85e5acd30509a827`
- source Alembic head: `a41c8e7d5b92`

این اطلاعات snapshot هستند و در شروع جلسه بعد باید دوباره بررسی شوند.

### baseline بازتأییدشده در ادامه پیاده‌سازی `2026-08-19`

- branch و HEAD محلی: `agent/heisenberg-v4.8.0@fd73e03d3dffff158f3354883224f5a4094de2d7` با working tree دارای تغییرات پیاده‌سازی مرحله ۲/۳.
- remote tag: شیء annotated برابر `466f4148dfe2f5c124618f62a57c1af53318f95d` و commit نهایی tag برابر `fd73e03d3dffff158f3354883224f5a4094de2d7`.
- GitHub API، Release دارای نشان `Latest` را `v4.8.0` با زمان انتشار `2026-08-18T00:36:33Z` اعلام کرد.
- remote branch: `agent/heisenberg-v4.8.0@fd73e03d3dffff158f3354883224f5a4094de2d7`؛ remote `master@0961983c2371867fe7b676f29318a3b0b32c1bde`.
- rollback application: `v4.8.0@fd73e03d3dffff158f3354883224f5a4094de2d7`؛ tag قبلی برای بازیابی اضطراری `v4.7.1@447d9265bd3738883709042f85e5acd30509a827`.
- GHCR snapshot معتبر قبلی برای `v4.8.0` و `latest`: `sha256:374b0e18d4daa289d99692256f3fb264ddd93eca9a1f752837d6d7a17e1ed9b8`؛ بازتأیید registry در این نوبت به‌علت timeout شبکه هنوز لازم است.
- میزبان فعلی Docker، Podman، MySQL Server/Client و WSL نصب‌شده ندارد. برای evidence واقعی مرحله ۲، MySQL Community Server `8.0` به‌صورت ZIP محلی و ایزوله آماده می‌شود.

## قانون ثبت پیشرفت و ادامه پس از قطع برق

این فایل مرجع اصلی ادامه کار است. در زمان پیاده‌سازی رعایت موارد زیر اجباری است:

1. پیش از شروع هر مرحله، بخش «نقطه دقیق ادامه» به همان مرحله تغییر کند.
2. پس از هر تغییر معنادار، یک ردیف به «لاگ پیشرفت» اضافه شود.
3. هر ردیف شامل زمان، مرحله، وضعیت، فایل‌های تغییرکرده، commit، آزمون‌ها، خطاها و قدم بعدی باشد.
4. پیش از اجرای migration، build، تست طولانی، commit یا انتشار، وضعیت در این فایل ثبت شود.
5. مرحله فقط پس از موفقیت آزمون‌های همان مرحله با `[x]` کامل علامت بخورد.
6. اگر کار نیمه‌کاره ماند، فایل‌های دارای تغییر و فرمان دقیق ادامه ثبت شوند.
7. پس از وصل مجدد برق، ابتدا این فایل، سپس `git status --short --branch` و آخرین ردیف لاگ خوانده شود. کار از «نقطه دقیق ادامه» ادامه پیدا کند؛ مراحل کامل دوباره اجرا نشوند.
8. هیچ تغییر مرتبطی در `marzhelp` یا `V2IpLimit` انجام نشود. محل تغییر فقط پروژه `Marzban` است.
9. هر گزارش پیشرفت دارای تغییر DB باید نتیجه upgrade از baselineهای فعلی، backfill
   واقعاً لازم و rollback application را نشان دهد؛ برای Stageهای 7 تا 13، داده legacy
   فرضی ساخته یا گزارش نشود.

## بهینه‌سازی سراسری دامنه Stageهای 7 تا 13 — تصمیم Owner در `2026-08-23`

> [!important] دامنه معتبر ادامه پروژه
> این deployment هرگز در production استفاده نشده و هیچ User/Admin/account/settings
> تاریخی production برای حفظ یا backfill وجود ندارد. این تصمیم فقط Stageهای 7 تا
> 13 را بهینه می‌کند؛ Stageهای PASS شده 0 تا 6 و evidence تاریخی آن‌ها بازنویسی یا
> دوباره‌اجرا نمی‌شوند مگر defect یا dependency conflict واقعی پیدا شود.

- migration امن از schema نصب `v4.9.8` و زنجیره فعلی پروژه الزامی است. head محلی
  هنگام ثبت این تصمیم `5b8d1f3a7c64` است؛ هر Stage head واقعی شروع خود را ثبت کند.
- compatibility لازم working tree فعلی حفظ شود. `LEGACY_COMPAT` پیاده‌شده باقی
  می‌ماند، اما بدون dependency واقعی توسعه داده نمی‌شود. کد legacy-related که در
  Stageهای PASS وجود دارد صرفاً برای cleanup حذف، rename یا rewrite نشود.
- ساخت backfill پیچیده، dataset مصنوعی و test matrix برای account/settings فرضی
  production ممنوع است؛ مگر migration فعلی، dependency واقعی یا invariant امنیتی/
  حسابداری آن را لازم کند.
- DB production فقط MySQL 8.x / InnoDB است. evidence مربوط به migration، transaction،
  locking، concurrency، index، query plan و performance فقط با MySQL واقعی معتبر
  است. SQLite فقط unit harness سریع است و PASS آن evidence DB production نیست.
- PostgreSQL و TimescaleDB در Stageهای باقی‌مانده پیاده‌سازی یا تست نشوند. مهاجرت
  آینده به `TimescaleDB -> PostgreSQL -> SQLAlchemy -> Alembic -> FastAPI/Marzban`
  پروژه‌ای مستقل است.
- الگوهای portable در SQLAlchemy/Alembic ترجیح دارند، اما correctness، transaction
  safety و performance فعلی MySQL قربانی portability نظری نشود. SQL/DDL/index/query
  خاص MySQL فقط هنگام ضرورت، ایزوله و با علت مستند استفاده شود.
- تست هر Stage: targeted + adjacent regression. ماتریس‌های قدیمی گران فقط وقتی
  تکرار شوند که رفتار مرتبط تغییر کرده باشد. پوشش security، accounting، hierarchy،
  authorization، idempotency، concurrency، ledger/refund، Plan/network scope،
  backup/restore و Telegram reliability کاهش پیدا نکند.
- تمرکز DB: Stage 7 رقابت delegation/freeze؛ Stage 8 bulk accounting و resume؛
  Stage 9 aggregate/query plan؛ Stage 10 pagination/index؛ Stage 11 outbox/scheduler/
  backup lock و restore؛ Stage 12 فقط در صورت اثر واقعی DB؛ Stage 13 migration و
  regression نهایی از baselineهای فعلی روی MySQL.
- ترتیب مرجع بدون تغییر است: `AGENTS.md`، سپس اسناد الزامی repository، سپس Runbook.
- commit، push، tag، release، deploy و publish تا دستور صریح همچنان ممنوع است.

## هدف نهایی

- تنها یک مدیر کل با نقش `Owner` وجود داشته باشد.
- سه نقش ثابت و ساده وجود داشته باشد: `Owner`، `Super Admin` و `Admin`؛ از ساخت ده‌ها گزینه دسترسی در فرم Admin جلوگیری شود.
- ساخت یا تعیین Owner فقط از shell سرور انجام شود؛ پنل و API نتوانند Owner یا sudo بسازند.
- `Super Admin` بتواند Admin و Super Admin زیرمجموعه بسازد و مدیریت کند؛ `Admin` نقش اجرایی بدون امکان ساخت Admin زیرمجموعه باشد.
- هر Admin فقط شاخه خودش، همه Adminهای پایین‌تر و کاربران متعلق به آن شاخه را ببیند و مدیریت کند.
- والد و خواهر/برادرها از دید Admin خارج باشند.
- اعتبار از والد به فرزند منتقل شود، از اعتبار قابل‌واگذاری والد کم شود و فرزند بتواند همین روند را برای نسل بعد ادامه دهد.
- تمام انتقال‌ها، تغییرات نقش، تغییر والد و عملیات حساس audit شوند.
- دسترسی API خارجی برای `Super Admin` و `Admin` پیش‌فرض خاموش باشد و فقط Owner بتواند آن را فعال، محدود یا لغو کند.
- مدیریت Nodeها، هسته Xray، تنظیمات سراسری و بازنشانی مصرف کل پنل فقط در اختیار Owner باشد.

## اصطلاحات قطعی پیشنهادی

- `Owner`: تنها مدیر کل، دارای دسترسی سراسری و زیرساختی.
- `Super Admin`: مدیر شاخه که می‌تواند Admin یا Super Admin زیرمجموعه بسازد و کل subtree خود را مدیریت کند.
- `Admin`: مدیر اجرایی که کاربران خودش را مدیریت می‌کند و نمی‌تواند Admin زیرمجموعه بسازد.
- `Parent Admin`: والد مستقیم.
- `Descendant Admin`: هر Admin پایین‌تر از شاخه، در هر عمق.
- `Own Users`: کاربران دارای `users.admin_id` برابر Admin.
- `Subtree Users`: کاربران Admin فعلی و تمام Descendantها.

این سه نام طبق تصمیم کاربر قطعی‌اند. واژه `sudo` فقط هنگام migration و سازگاری نسخه قدیمی استفاده شود و از رابط نهایی حذف شود. نام داخلی CLI و schema باید مستقل از ترجمه رابط باقی بماند.

## وضعیت فعلی پروژه

- نقش فعلی فقط با `admins.is_sudo` مشخص می‌شود.
- هر `is_sudo=true` دسترسی سراسری دارد.
- Admin عادی فقط کاربری را می‌بیند که `users.admin_id` آن دقیقاً برابر شناسه خودش باشد.
- هیچ رابطه والد/فرزند میان Adminها وجود ندارد.
- پنل فعلی اجازه ساخت Admin با `is_sudo=true` می‌دهد.
- CLI فعلی نیز هنگام `admin create` یا `admin update` مقدار sudo را می‌پذیرد.
- متغیرهای `SUDO_USERNAME` و `SUDO_PASSWORD` یک مسیر ورود sudo خارج از رکورد عادی DB ایجاد می‌کنند.
- فرمان فعلی `admin import-from-env` کاربران بدون مالک را به sudo واردشده متصل می‌کند.
- اعتبار فعلی در `marzhelp_admin_settings.total_traffic` نگهداری می‌شود، اما اعتبار واگذارشده به فرزندان هنوز مدل نشده است.
- ستون‌های `renewal_limit` و `renewals_used` در schema فعلی وجود دارند، اما enforcement کامل آن‌ها در مسیر `validate_update` مشاهده نشد.
- حالت `calculate_volume="created_traffic"` و شمارنده حجم تخصیص‌یافته از قبل وجود دارد و باید به‌جای ایجاد حسابداری موازی، اصلاح و در UI شفاف شود.
- endpoint فعلی `POST /api/admin/{username}/users/disable` فقط sudo است، فقط کاربران مستقیم یک Admin را هدف می‌گیرد و پس از update کل Core و Nodeهای متصل را restart می‌کند.
- `UserTemplate` فعلی سراسری است، نام global unique دارد، مالک/نسخه/وراثت سلسله‌مراتبی ندارد و ساخت/ویرایش/حذف آن فقط sudo است.

## تکلیف sudoهای فعلی هنگام ایجاد Owner

مهاجرت پیشنهادی باید اتمیک و بدون حذف Admin یا User باشد:

1. ابتدا فهرست تمام Adminهای DB با `is_sudo=true` و sudo تعریف‌شده در env نمایش داده شود.
2. اپراتور سرور دقیقاً یک Admin موجود را با فرمان زیر به Owner تبدیل کند:

```bash
marzban set-owner <username>
```

3. فرمان داخلی پیشنهادی:

```bash
marzban-cli admin set-owner --username <username>
```

4. Admin انتخاب‌شده Owner شود.
5. تمام sudoهای DB دیگر به `Super Admin` سطح اول تبدیل شوند:
   - `is_sudo=false`
   - والد مستقیم آن‌ها Owner باشد.
   - کاربران فعلی‌شان با همان `users.admin_id` حفظ شوند.
   - دسترسی سراسری آن‌ها حذف شود؛ فقط شاخه خودشان را ببینند.
   - امکان مدیریت و ساخت زیرمجموعه را داشته باشند، اما هیچ مجوز Owner-only نگیرند.
   - دسترسی API خارجی آن‌ها پیش‌فرض خاموش باشد تا Owner صریحاً آن را فعال کند.
6. تمام Adminهای عادی فعلی که والد ندارند با نقش `Admin` فرزند مستقیم Owner شوند.
7. تمام کاربران دارای `admin_id=NULL` به Owner متصل شوند.
8. sudo تعریف‌شده در env ابتدا به رکورد DB تبدیل شود؛ سپس مسیر bypass مبتنی بر `SUDO_USERNAME` و `SUDO_PASSWORD` غیرفعال شود.
9. تا زمانی که Owner با موفقیت تعیین نشده، حالت سلسله‌مراتبی فعال نشود و migration از نیمه عبور نکند.
10. نتیجه migration شامل Owner انتخاب‌شده، sudoهای تبدیل‌شده، Adminهای متصل‌شده و کاربران بدون مالک ثبت شود.

نتیجه مهم: sudoهای فعلی حذف نمی‌شوند و کاربرانشان جابه‌جا نمی‌شوند؛ sudo انتخاب‌شده Owner و بقیه sudoها Super Admin مستقیم Owner می‌شوند. Adminهای معمولی فعلی با نقش Admin حفظ می‌شوند.

## قواعد دسترسی

### Owner

- مشاهده و مدیریت تمام Adminها و Userها.
- تعیین والد، انتقال شاخه، بازیابی اعتبار و مشاهده audit سراسری.
- تنظیم اعتبار اولیه یا افزایش اعتبار سیستم.
- تعیین Owner بعدی فقط از shell سرور، نه پنل.
- تنها نقش مجاز برای مشاهده و مدیریت Nodeها، تنظیمات و لاگ Node، هسته Xray، پیکربندی Core و restart آن.
- تنها نقش مجاز برای بازنشانی مصرف همه کاربران کل پنل و اجرای عملیات سراسری غیرقابل‌محدودسازی به subtree.
- تنها نقش مجاز برای مشاهده آمار واقعی کل سیستم، کل مصرف پنل، پهنای‌باند ورودی/خروجی و وضعیت زیرساخت.
- تنها نقش مجاز برای فعال‌سازی، محدودسازی، لغو یا مشاهده تنظیم دسترسی API خارجی Adminها.

### Super Admin

- مشاهده و مدیریت خودش، Descendantها و کاربران کل subtree خودش.
- ساخت `Admin` یا `Super Admin` در subtree، بدون امکان ساخت Owner یا اعطای مجوز Owner-only.
- مدیریت نقش، وضعیت و اعتبار Descendantها در محدوده‌ای که از والد دریافت کرده است.
- عدم مشاهده یا تغییر والد، اجداد، خواهر/برادرها، شاخه‌های دیگر، Nodeها، Core و آمار سراسری.
- انتقال اعتبار فقط به فرزند مستقیم یا Descendant مجاز خودش.
- عدم انتقال اعتبار به خودش، والد، اجداد یا شاخه دیگر.

### Admin

- مشاهده و مدیریت حساب خودش و Own Users.
- عدم ساخت، حذف یا تغییر Admin دیگر.
- عدم مشاهده والد، اجداد، خواهر/برادرها، شاخه‌های دیگر، Nodeها، Core و آمار سراسری.
- امکان فعال‌سازی، غیرفعال‌سازی، reset مصرف، revoke، ویرایش، حذف و bulk action فقط برای Own Users.
- دسترسی API خارجی پیش‌فرض خاموش و غیرقابل‌تغییر توسط خودش.

### مدیریت کاربران در سلسله‌مراتب

- Owner تمام Userهای پنل را مدیریت کند.
- Super Admin تمام Userهای Own Users و Descendantها را مدیریت کند.
- Admin تمام Own Users خودش را مدیریت کند.
- Admin بالاسری بتواند همان عملیات قابل‌اجرا توسط صاحب مستقیم User را انجام دهد: فعال‌سازی، غیرفعال‌سازی، ویرایش، reset مصرف، revoke، حذف و bulk action.
- عملیات پاکسازی موجود Marzban برای حساب‌های منقضی یا حذف‌شده فقط روی subtree مجاز اجرا شود؛ پاکسازی سراسری فقط Owner.
- scope هم هنگام انتخاب Userها و هم بلافاصله پیش از write دوباره در backend بررسی شود تا payload دست‌ساز یا race موجب دسترسی بین شاخه‌ها نشود.

### قاعده عدم ارتقای مجوز

مجوز مؤثر فرزند از preset نقش و محدودیت والد محاسبه شود. `Super Admin` نمی‌تواند Owner بسازد یا مجوز Owner-only و API خارجی اعطا کند. فرزند نمی‌تواند با payload دست‌ساز API این محدودیت را دور بزند.

### دسترسی API خارجی

منظور از «دسترسی API» در این سند، استفاده خارجی و automation از API است. خود پنل Marzban برای کارکردن از endpointهای backend استفاده می‌کند؛ بنابراین خاموش‌بودن API خارجی نباید ورود به پنل یا عملیات مجاز و scope‌شده پنل را خراب کند.

- `Owner`: دسترسی کامل API و تنها نقش مجاز برای مدیریت دسترسی دیگران.
- `Super Admin` و `Admin`: `external_api_enabled=false` به‌صورت پیش‌فرض.
- Admin نتواند API خودش یا فرزندش را فعال کند؛ این اختیار قابل‌واگذاری نیست.
- token خارجی از session پنل جدا باشد و دارای scope، زمان انقضا، آخرین استفاده و revoke باشد.
- token و secret خام در DB ذخیره نشود؛ فقط hash امن نگهداری شود.
- غیرفعال‌کردن API باید tokenهای فعال همان Admin را فوراً revoke کند.
- تمام ایجاد، لغو، شکست ورود و استفاده حساس API audit شود.

### داشبورد غیر Owner

`Super Admin` و `Admin` نباید مشخصات سرور، Node، Core، مصرف واقعی کل پنل یا پهنای‌باند سراسری را دریافت کنند؛ فقط مخفی‌کردن UI کافی نیست و پاسخ backend نیز نباید این داده‌ها را برگرداند.

داشبورد آن‌ها با «خلاصه حساب» جایگزین شود:

- اعتبار کل دریافتی، مصرف‌شده، واگذارشده و قابل‌واگذاری.
- تعداد کاربران خود و subtree به تفکیک فعال، غیرفعال، محدود، منقضی و در انتظار.
- تعداد Super Admin و Admin زیرمجموعه؛ برای Admin معمولی صفر و بدون بخش مدیریت زیرمجموعه.
- مصرف Own Users و مصرف تجمیعی subtree، بدون نمایش مصرف کل پنل.
- هشدار کمبود اعتبار، کاربران نزدیک انقضا، عملیات ناموفق و رخدادهای Device Limit در scope خودش.
- آخرین فعالیت‌های خودش و Descendantها: ساخت/ویرایش/حذف User، تغییر وضعیت، انتقال اعتبار و تغییر Admin.
- فهرست کوتاه فعالیت با pagination؛ بدون query نامحدود یا بارگیری همه logها.

Owner داشبورد کامل فعلی Marzban را همراه با خلاصه سراسری، Node، Core و عملیات reset کل حفظ کند.

## محدودیت‌های Admin و قطع خودکار

### مجوز و سهمیه تمدید

دو مفهوم جدا و با نام روشن وجود داشته باشد:

- `renewal_enabled`: آیا Admin اصولاً اجازه تمدید User دارد یا نه.
- `renewal_limit`: تعداد تمدید مجاز؛ `NULL` یعنی نامحدود و صفر یعنی هیچ تمدیدی باقی نمانده است.

قواعد:

- Owner برای Super Admin و Admin این تنظیم را تعیین کند.
- Super Admin فقط در محدوده مجوز دریافتی خودش برای Descendantها مقدار برابر یا محدودتر تعیین کند؛ هرگز نتواند تمدید ممنوع‌شده توسط والد را فعال کند.
- هر تمدید موفق دقیقاً یک واحد از سهمیه کم کند؛ درخواست شکست‌خورده یا retry با همان idempotency key دوباره کم نکند.
- تغییر حجم، تاریخ، Next Plan یا reset فقط زمانی تمدید حساب شود که قرارداد دقیق `_is_renewal` آن را renewal تشخیص دهد؛ این قرارداد با testهای مستقل قفل شود.
- وقتی تمدید ممنوع است، دکمه UI حذف/غیرفعال و endpoint backend با `403` رد شود.
- شمارنده‌های فعلی `renewal_limit` و `renewals_used` یا به مدل واحد و اتمیک تبدیل شوند یا یکی حذف شود؛ دو منبع حقیقت باقی نماند.

### محاسبه حجم بر مبنای حجم ساخته‌شده

- برای حسابداری `Super Admin` و `Admin` حالت پیش‌فرض `created_traffic` باشد؛ یعنی حجم تخصیص‌یافته هنگام ساخت یا تمدید User از اعتبار Admin کم شود، نه ترافیک واقعی مصرف‌شده.
- این حالت فقط حسابداری Admin را تغییر دهد؛ آمار واقعی User، Core، Node و Owner همچنان از ترافیک واقعی محاسبه شود.
- حذف User، کاهش حجم یا reset مصرف نباید اعتبار مصرف‌شده بر مبنای حجم ساخته‌شده را خودکار برگرداند.
- ساخت و تمدید plan-based نیز از همان ledger و شمارنده canonical استفاده کند و مسیر حسابداری جدا نسازد.
- عنوان UI پیشنهادی: «مصرف اعتبار بر اساس حجم تخصیص‌یافته»؛ مقدار «حجم واقعی مصرف‌شده» فقط در جزئیات User و گزارش‌های مجاز باقی بماند.

### قطع خودکار Admin پس از اتمام محدودیت

موردهای ۳ و ۵ درخواست کاربر تکراری‌اند و به‌عنوان یک نیاز بحرانی ثبت شدند.

محرک‌های قطع کامل پیشنهادی:

- پایان تاریخ اعتبار Admin.
- تمام‌شدن اعتبار حجم Admin بر اساس mode حسابداری خودش.
- غیرفعال‌سازی دستی توسط Parent مجاز یا Owner.

رسیدن به `max_users`، تمام‌شدن سهمیه تمدید یا تمام‌شدن سهمیه ساخت فقط همان عملیات را متوقف کند و باعث قطع Userهای موجود نشود. این تفکیک جلوی قطع ناخواسته کل مشتریان به‌دلیل پرشدن ظرفیت ساخت را می‌گیرد.

رفتار قطع کامل:

1. وضعیت Admin به `SUSPENDED` تغییر کند و دلیل، زمان، عامل و snapshot محدودیت ثبت شود.
2. تمام Own Users و در صورت Super Admin بودن، تمام Userهای subtree از Core و Nodeها قطع و در DB غیرفعال شوند.
3. mutationهای پنل، API خارجی و ساخت/تمدید فوراً رد شوند؛ فقط صفحه read-only دلیل تعلیق و وضعیت حساب قابل‌نمایش باشد.
4. job دوره‌ای و check هم‌زمان در مسیر درخواست وجود داشته باشد تا وابسته به cron تنها نباشد.
5. عملیات idempotent باشد؛ اجرای دوباره، audit و شمارنده تکراری نسازد.
6. پس از رفع محدودیت، فقط Userهایی که به‌علت همین suspension غیرفعال شده‌اند قابل‌بازیابی باشند؛ Userهایی که قبلاً دستی disabled، expired یا limited بوده‌اند فعال نشوند.
7. قطع و بازیابی روی batchهای محدود انجام شود؛ transaction یا query نامحدود روی میلیون‌ها User ممنوع.

### غیرفعال‌سازی همه کاربران یک Admin

- خود Admin بتواند تمام Own Users خودش را غیرفعال کند.
- Super Admin بتواند Own Users، کاربران یک Descendant مشخص یا تمام subtree خودش را غیرفعال کند.
- Owner بتواند یک شاخه یا کل پنل را انتخاب کند؛ عملیات کل پنل همچنان Owner-only باشد.
- پیش از اجرا، تعداد هدف و scope دقیق نمایش داده شود و تأیید صریح گرفته شود.
- backend scope را دوباره بررسی کند و عملیات با `operation_id` idempotent ثبت شود.
- برای حجم بالا، update و sync Xray/Node به‌صورت chunked و قابل‌ادامه باشد؛ restart سراسری برای هر درخواست مسیر پیش‌فرض نباشد.
- نتیجه شامل تعداد موفق، ناموفق، قبلاً غیرفعال و خطاهای sync باشد و در audit قابل مشاهده بماند.
- فعال‌سازی گروهی عملیات جدا باشد و status قبلی را کورکورانه به `active` تبدیل نکند.

## سیستم Plan برای ساخت و تمدید User

### حالت ساخت User برای هر Admin

دو mode ساده وجود داشته باشد:

- `FREE_FORM`: Admin در محدوده مجوزها می‌تواند حجم، تاریخ، limit و گزینه‌های مجاز را دستی انتخاب کند.
- `PLAN_ONLY`: Admin فقط از planهای مجاز User بسازد یا تمدید کند و نتواند با UI یا payload دستی حجم، تاریخ، limit، inbound یا Next Plan را تغییر دهد.

Parent مجاز هنگام ساخت یا ویرایش Admin، mode را تعیین کند. فرزند نتواند mode محدود `PLAN_ONLY` را به `FREE_FORM` تغییر دهد.

### مالکیت و وراثت Plan

- Owner بخش «Planهای پیش‌فرض» داشته باشد و planهای سراسری بسازد.
- Super Admin فقط وقتی `can_manage_plans=true` دارد بتواند plan بسازد، ویرایش کند یا archive کند.
- `Admin` عادی نتواند plan بسازد.
- Super Admin دارای مجوز ساخت plan فقط در محدوده اعتبار، مدت، inbound، concurrent limit و مجوزهای دریافت‌شده از والد plan بسازد.
- اگر `can_manage_plans=false` باشد، Admin یا Super Admin از planهای فعال والد بالاسری پیروی کند.
- plan ارث‌رسیده read-only باشد؛ فرزند نتواند آن را ویرایش کند.
- Parent بتواند تعیین کند کدام planها به کدام فرزند یا subtree قابل‌استفاده‌اند.
- حذف فیزیکی plan استفاده‌شده ممنوع؛ plan ابتدا archive شود و snapshot نسخه اعمال‌شده روی User باقی بماند.
- تغییر plan نباید Userهای قدیمی را بی‌صدا تغییر دهد؛ فقط ساخت یا تمدید بعدی از نسخه جدید استفاده کند.

### داده‌های حداقلی Plan

- نام و توضیح کوتاه.
- حجم مجاز.
- مدت اعتبار.
- محدودیت اتصال هم‌زمان User.
- strategy بازنشانی مصرف.
- inboundها و protocolهای مجاز.
- رفتار باقی‌مانده حجم هنگام تمدید.
- وضعیت فعال یا archived.
- نوع استفاده: ساخت، تمدید یا هر دو.

### فرم ساخت و تمدید در حالت `PLAN_ONLY`

فرم ساخت User فقط این موارد را نشان دهد:

- username.
- انتخاب plan مجاز.
- note اختیاری.
- خلاصه read-only حجم، مدت، limit و inboundهای plan پیش از تأیید.

فیلدهای دستی حجم، تاریخ، concurrent limit، inbound، protocol، reset strategy و Next Plan مخفی و در backend نیز ممنوع شوند.

صفحه User دو عملیات واضح داشته باشد:

- «ساخت User جدید» با plan.
- «تمدید User» با انتخاب plan تمدید مجاز و نمایش نتیجه حجم/تاریخ قبل از تأیید.

تمدید باید `renewal_enabled`، `renewal_limit`، اعتبار حجم، دسترسی plan، scope User و version plan را در یک transaction بررسی کند.

## باگ‌های ثبت‌شده

### `BUG-ADM-001` — محدودیت دستگاه/IP هم‌زمان User اعمال نمی‌شود

- وضعیت: `OPEN_BLOCKED_BY_BUG-DVL-003`
- گزارش تکمیلی کاربر: منظور `concurrent_user_limit` و تشخیص دستگاه/IP اضافه است، نه `max_users` یا سهمیه عملیات Admin.
- وابستگی: تا pipeline مشاهده IP در `BUG-DVL-003` درست نشود، engine داده کافی برای تشخیص عبور از limit ندارد.
- بررسی اجباری: ذخیره `concurrent_user_limit`، فعال‌بودن Device Limit، slotها، observation window، dedup IP، threshold، penalty stage و اجرای action روی Core/Node.
- پذیرش: با limit برابر `1`، اتصال IP دوم در بازه تعریف‌شده مشاهده و incident ثبت شود؛ action تنظیم‌شده اجرا شود؛ IP تکراری یک دستگاه دوباره شمرده نشود؛ restart سرویس state را خراب نکند.

### `BUG-USR-002` — غیرفعال‌کردن User مؤثر نیست

- وضعیت: `OPEN`
- گزارش کاربر: پس از غیرفعال‌کردن، اکانت عملاً غیرفعال نمی‌شود.
- بررسی اجباری: ذخیره `User.status` در DB، پاسخ API، حذف credential از Core محلی، تمام Nodeها و slotهای device، cache و subscription.
- نقاط مشکوک برای بررسی، نه علت قطعی: اجرای `xray.operations.remove_user` در BackgroundTask با ORM object، swallowشدن خطاهای Xray/Node و شرط status در مسیر reset.
- پذیرش: بعد از پاسخ موفق، status در DB برابر `disabled` باشد؛ اتصال قبلی و اتصال جدید روی Core و تمام Nodeهای متصل قطع شود؛ restart سرویس باعث برگشت User نشود؛ خطای sync قابل‌مشاهده و قابل retry باشد.

### `BUG-DVL-003` — IP و لاگ اتصال در پنل ثبت/نمایش داده نمی‌شود

- وضعیت: `OPEN_CRITICAL`
- گزارش کاربر: پنل هیچ IP یا log قابل‌استفاده‌ای نشان نمی‌دهد و در نتیجه مشخص نیست User دستگاه اضافه استفاده کرده یا نه.
- اثر: blocker مستقیم `BUG-ADM-001` و هر penalty مبتنی بر تعداد دستگاه/IP.
- مسیر بررسی: دریافت observation از Core محلی و تمام Nodeها، parsing email/slot، نگاشت به `user_id`، ثبت `last_ip` و state، retention، mask/full-IP permission، API خلاصه User و UI Device Limit.
- بررسی جداگانه انجام شود که داده واقعاً وارد DB نمی‌شود یا فقط API/UI آن را فیلتر یا mask می‌کند.
- خطای Node/Core نباید swallow شود؛ source node، زمان آخرین observation، آخرین خطا و سلامت collector در پنل Owner قابل‌مشاهده باشد.
- پذیرش: اتصال آزمایشی از دو IP مشخص در DB و API دیده شود؛ Admin مجاز IP mask‌شده و Owner IP کامل را ببیند؛ source node و زمان ثبت درست باشد؛ پس از retention فقط داده مجاز پاک شود؛ incident limit از همین داده ساخته شود.

### قالب ثبت باگ‌های بعدی

برای هر باگ جدید این موارد ثبت شود: شناسه، نسخه، نقش، مسیر UI/API، مراحل بازتولید، انتظار، نتیجه واقعی، log، داده DB قبل/بعد، وضعیت Core/Node، severity، test بازگشتی و وضعیت رفع.

## قرارداد قفل‌شده مرحله ۱

- فرمان عمومی نهایی تعیین Owner: `marzban set-owner <username>`؛ فرمان داخلی: `marzban-cli admin set-owner --username <username>`.
- مرحله اول حسابداری فقط اعتبار حجم را منتقل می‌کند؛ پول، تعداد User و سهمیه تمدید ledger جدا ندارند.
- `Reparent` کل subtree در نسخه اول فقط Owner است. `Super Admin` نمی‌تواند Parent هیچ شاخه‌ای را تغییر دهد.
- Admin تعریف‌شده در env خودکار Owner نمی‌شود. در زمان `set-owner` ابتدا رکورد DB آن ساخته یا همگام می‌شود؛ پس از backfill موفق، bypass مبتنی بر env غیرفعال می‌شود.
- مدل DB عمق نامحدود دارد؛ service برای هر mutation عمق `64` را سقف عملیاتی قرار می‌دهد و migration قبل از فعال‌سازی hierarchy عمق بیشتر را گزارش می‌کند.
- API خارجی فقط token مستقل automation است. session پنل و endpointهای scope‌شده UI به `external_api_enabled` وابسته نیستند.
- Admin معلق می‌تواند وارد پنل شود، اما فقط داشبورد read-only دلیل تعلیق و وضعیت حساب را می‌بیند.
- پایان اعتبار حجم یا تاریخ `Super Admin` کل subtree او را suspend می‌کند؛ `max_users` و سهمیه ساخت/تمدید فقط همان عملیات جدید را مسدود می‌کنند.
- migration هیچ Plan پیش‌فرضی ایجاد نمی‌کند؛ Owner پس از فعال‌سازی hierarchy Planهای اولیه را صریحاً می‌سازد.
- رفتار تمدید داخل version هر Plan ذخیره می‌شود. پیش‌فرض نسخه اول: جایگزینی سقف حجم و تمدید زمان از `max(now, current_expire)`.
- دسترسی Plan به فرزند با allowlist صریح است؛ انتشار به کل subtree فقط با گزینه مستقل و پیش‌فرض خاموش انجام می‌شود.
- نبود log و reproduction دو باگ مانع schema سلسله‌مراتب نیست، اما مرحله ۶ را تا دریافت شواهد واقعی مسدود نگه می‌دارد.

## مدل پیشنهادی دیتابیس MySQL/InnoDB

### تغییر جدول `admins`

- `parent_admin_id BIGINT NULL`
- `role_id SMALLINT NOT NULL` با foreign key به lookup table نقش‌ها؛ از `ENUM` و مجموعه checkboxهای پراکنده استفاده نشود.
- `external_api_enabled BOOLEAN NOT NULL DEFAULT FALSE`
- `external_api_updated_by BIGINT NULL`
- `external_api_updated_at DATETIME NULL`
- `hierarchy_enabled BOOLEAN NOT NULL DEFAULT TRUE` در صورت نیاز به rollout مرحله‌ای
- index: `ix_admins_parent_id (parent_admin_id, id)`
- index متناسب با query نقش‌های یک subtree فقط پس از بررسی `EXPLAIN ANALYZE` افزوده شود؛ over-indexing ممنوع.
- foreign key خودارجاع به `admins.id` با رفتار حذف کنترل‌شده در application؛ حذف cascade مستقیم ممنوع.

lookup table `admin_roles` حداقل سه مقدار ثابت داشته باشد:

- `OWNER`
- `SUPER_ADMIN`
- `ADMIN`

قواعد داده‌ای: Owner بدون والد، Super Admin و Admin دارای والد، و Admin اجازه داشتن فرزند نداشته باشد. این قواعد در service و آزمون migration کنترل شوند.

### تکمیل تنظیمات محدودیت Admin

در `marzhelp_admin_settings` یا جدول canonical جایگزین:

- `renewal_enabled BOOLEAN NOT NULL DEFAULT TRUE`
- یک مدل واحد برای مانده تمدید؛ استفاده هم‌زمان و مبهم از `renewal_limit` و `renewals_used` ممنوع.
- `user_creation_mode_id` با lookup مقادیر `FREE_FORM` و `PLAN_ONLY`؛ از `ENUM` استفاده نشود.
- `can_manage_plans BOOLEAN NOT NULL DEFAULT FALSE`
- `account_status_id` با lookup مقادیر حداقل `ACTIVE`، `SUSPENDED` و `DISABLED`.
- `suspended_reason_id NULL`
- `suspended_at DATETIME NULL`
- `suspended_by_admin_id BIGINT NULL`
- `suspension_event_id BIGINT NULL`

برای migration سازگار، Adminهای موجود ابتدا `FREE_FORM`، `renewal_enabled=true` و بدون تغییر ناگهانی رفتار وارد شوند؛ سپس Parent یا Owner آن‌ها را صریحاً محدود کند. حالت حسابداری `created_traffic` برای Adminهای جدید پیش‌فرض شود، ولی تغییر Adminهای قدیمی فقط با baseline و گزارش اختلاف انجام شود.

### Owner یکتا

برای تضمین دقیق یک Owner از جدول singleton استفاده شود:

- `system_owner.id` با مقدار ثابت `1` به‌عنوان primary key
- `system_owner.admin_id` به‌صورت `UNIQUE NOT NULL`
- foreign key به `admins.id`

این طراحی از اتکا به شرط ناقص یا race روی چند ردیف `is_owner=true` جلوگیری می‌کند.

### مسیرهای سلسله‌مراتبی

منبع اصلی رابطه `admins.parent_admin_id` باشد. برای سرعت queryهای subtree در مقیاس بزرگ، closure table افزوده شود:

- `admin_hierarchy.ancestor_id`
- `admin_hierarchy.descendant_id`
- `admin_hierarchy.depth`
- primary key: `(ancestor_id, descendant_id)`
- index معکوس: `(descendant_id, ancestor_id, depth)`
- هر Admin یک self-row با `depth=0` داشته باشد.

ساخت، انتقال و حذف شاخه باید `admins` و `admin_hierarchy` را در یک transaction هماهنگ تغییر دهد. چرخه والد/فرزند باید پیش از write رد شود.

### حساب اعتبار

در مرحله اول فقط اعتبار حجم منتقل شود. فیلدهای پیشنهادی در تنظیمات Admin:

- `total_traffic`: کل اعتبار دریافت‌شده Admin
- `delegated_traffic`: اعتبار رزروشده برای فرزندان
- مصرف شخصی طبق مدل فعلی `used_traffic` یا `created_traffic`

فرمول اعتبار قابل‌واگذاری:

```text
available = total_traffic - own_spend - delegated_traffic
```

انتقال اعتبار باید در یک transaction انجام شود:

1. ردیف‌های والد و فرزند با ترتیب ثابت شناسه و `SELECT ... FOR UPDATE` قفل شوند.
2. subtree و رابطه مجاز تأیید شود.
3. کافی‌بودن `available` والد بررسی شود.
4. `delegated_traffic` والد افزایش یابد.
5. `total_traffic` فرزند افزایش یابد.
6. ledger ثبت شود.
7. commit انجام شود؛ در هر خطا کل عملیات rollback شود.

### ledger انتقال اعتبار

جدول `admin_credit_transfers`:

- `id BIGINT UNSIGNED AUTO_INCREMENT`
- `from_admin_id`
- `to_admin_id`
- `actor_admin_id`
- `amount BIGINT`
- `operation_type`: `grant`, `reclaim`, `owner_adjustment`, `migration`
- `idempotency_key VARCHAR(...) UNIQUE`
- `created_at DATETIME`
- `note`
- index `(from_admin_id, created_at, id)`
- index `(to_admin_id, created_at, id)`
- index `(actor_admin_id, created_at, id)`

برای جلوگیری از deadlock، قفل walletها همیشه به ترتیب صعودی `admin_id` گرفته شود. برای خطای MySQL `1213` retry محدود با backoff کوتاه در نظر گرفته شود.

### tokenهای API خارجی

جدول پیشنهادی `admin_api_tokens`:

- `id BIGINT UNSIGNED AUTO_INCREMENT`
- `admin_id BIGINT NOT NULL`
- `token_hash VARBINARY(...) NOT NULL`
- `name VARCHAR(...) NOT NULL`
- `scopes` با طراحی normalized یا JSON محدود و validateشده پس از بررسی الگوی واقعی endpointها
- `expires_at DATETIME NOT NULL`
- `last_used_at DATETIME NULL`
- `revoked_at DATETIME NULL`
- `created_by_admin_id BIGINT NOT NULL` که برای این نسخه باید Owner باشد
- index `(admin_id, revoked_at, expires_at, id)`

session ورود پنل از این جدول جدا بماند. rate limit، rotation و cleanup دوره‌ای tokenهای منقضی در طراحی نهایی لحاظ شود.

### جدول‌های Plan

طرح اولیه که باید با queryهای واقعی و `EXPLAIN ANALYZE` نهایی شود:

- `admin_user_plans`: مالک، نام، توضیح، active/archive، نوع ساخت/تمدید و نسخه جاری.
- `admin_user_plan_versions`: snapshot تغییرناپذیر حجم، مدت، concurrent limit، reset strategy و رفتار تمدید.
- `admin_user_plan_inbounds`: رابطه normalized میان version و inbound.
- `admin_user_plan_access`: دسترسی صریح plan به Admin یا subtree در صورت نیاز.
- `user_plan_assignments`: User، plan، version اعمال‌شده، actor و زمان ساخت/تمدید.

indexهای پایه پیشنهادی:

- plan فعال یک مالک: `(owner_admin_id, archived_at, id)`
- versionهای یک plan: `(plan_id, version_number)` با unique constraint.
- دسترسی plan: `(admin_id, plan_id)` و index معکوس `(plan_id, admin_id)`.
- سابقه User: `(user_id, created_at, id)`.

نام plan فقط داخل scope مالک unique باشد؛ unique سراسری فعلی `user_templates.name` برای سلسله‌مراتب مناسب نیست. migration باید templateهای فعلی را بدون حذف به Owner منتقل یا به plan سراسری تبدیل کند.

### رخداد تعلیق و بازیابی

برای بازیابی امن statusها:

- `admin_suspension_events`: Admin هدف، actor، reason، snapshot محدودیت، started/resolved و status پردازش.
- `admin_suspension_users`: event، User، status قبلی، status اعمال‌شده و sync status.
- primary/unique مناسب روی `(event_id, user_id)` برای idempotency.
- index پردازش batch روی `(event_id, sync_status, user_id)` تا job بدون `OFFSET` و با cursor ادامه پیدا کند.

این جدول‌ها مانع فعال‌شدن اشتباه Userهایی می‌شوند که پیش از suspension به‌صورت دستی disabled یا expired بوده‌اند.

## قواعد پس‌گرفتن اعتبار

- والد فقط اعتبار مصرف‌نشده و واگذارنشده فرزند را پس بگیرد.
- اعتبار مصرف‌شده هرگز با حذف User یا Admin احیا نشود.
- reclaim نباید `total_traffic` فرزند را کمتر از `own_spend + delegated_traffic` کند.
- حذف Admin بدون تعیین تکلیف اعتبار و فرزندان ممنوع باشد.

## رفتار حذف یا انتقال Admin

سه عملیات جدا و صریح:

1. `Reparent`: انتقال کل شاخه به والد جدید مجاز.
2. `Disable subtree`: غیرفعال‌سازی Admin و کاربران subtree بدون حذف داده.
3. `Delete leaf`: حذف فقط Admin بدون فرزند، پس از تعیین تکلیف کاربران و اعتبار.

حذف recursive در نسخه اول ممنوع باشد. این محدودیت احتمال حذف تصادفی یک شاخه بزرگ را کم می‌کند.

## APIهای پیشنهادی

- `GET /api/admin-management/tree`
- `POST /api/admin-management/{username}/children`
- `PUT /api/admin-management/{username}/parent`
- `POST /api/admin-management/{username}/credit/grant`
- `POST /api/admin-management/{username}/credit/reclaim`
- `GET /api/admin-management/{username}/credit/ledger`
- `PUT /api/admin-management/{username}/external-api` — فقط Owner
- `POST /api/admin-management/{username}/api-tokens` — فقط Owner
- `DELETE /api/admin-management/{username}/api-tokens/{token_id}` — فقط Owner
- `GET /api/account/summary` — خلاصه scope فعلی، بدون اطلاعات زیرساخت برای غیر Owner
- `GET /api/account/activity` — audit محدود به actor و subtree مجاز
- `PUT /api/admin-management/{username}/renewal-policy`
- `PUT /api/admin-management/{username}/user-creation-mode`
- `POST /api/admin-management/{username}/users/disable` — scope: own، یک Descendant یا subtree
- `POST /api/admin-management/{username}/suspend`
- `POST /api/admin-management/{username}/resume`
- `GET /api/user-plans`
- `POST /api/user-plans` — Owner یا Super Admin دارای `can_manage_plans`
- `PUT /api/user-plans/{plan_id}` — ایجاد version جدید، نه بازنویسی snapshot قدیمی
- `DELETE /api/user-plans/{plan_id}` — archive منطقی
- `POST /api/users/from-plan`
- `POST /api/users/{username}/renew-from-plan`

تمام endpointها باید scope را در backend بررسی کنند. مخفی‌کردن دکمه در UI به‌تنهایی کنترل دسترسی محسوب نمی‌شود.

هر endpoint ساخت/تمدید plan-based باید فیلدهای دستی خارج از قرارداد را reject کند، نه اینکه آن‌ها را بی‌صدا نادیده بگیرد. عملیات مالی، تمدید و assignment باید idempotency key داشته باشند.

## دامنه queryهایی که باید اصلاح شوند

- فهرست، جستجو، آمار و export کاربران
- دریافت، ویرایش، حذف، reset، revoke و bulk action کاربر
- پاکسازی حساب‌های منقضی/حذف‌شده در scope مجاز
- انتقال مالک User
- Device Limit، هشدارها و عملیات unblock/reset
- گزارش‌ها، notificationها و audit logها
- فهرست و مدیریت Adminها
- شمارنده‌ها و quota summary در سطح subtree
- `get_system_stats`: پاسخ Owner سراسری و پاسخ غیر Owner فقط خلاصه حساب؛ داده حساس اصلاً serialize نشود.
- تمام routeهای `node` و `core`: فقط Owner در dependency backend، شامل HTTP و WebSocket.
- reset کل پنل: فقط Owner؛ reset یک User یا subtree طبق scope نقش.
- فهرست planهای مؤثر با join سلسله‌مراتب و pagination؛ بارگیری planهای همه اجداد و فیلتر در Python ممنوع.
- job تعلیق و غیرفعال‌سازی گروهی با cursor بر `users.id` و batch محدود؛ `OFFSET` روی جدول بزرگ ممنوع.
- audit عملیات گروهی به‌صورت summary و event ذخیره شود؛ ساخت یک payload بسیار بزرگ از تمام usernameها ممنوع.

برای Userهای subtree، query باید از join با `admin_hierarchy` استفاده کند و مستقیم روی مجموعه بزرگ شناسه‌ها در Python یا `IN (...)` نامحدود تکیه نکند.

## تغییرات پنل

- حذف کامل گزینه ساخت یا تغییر sudo از پنل.
- نمایش badgeهای `Owner`، `Super Admin` و `Admin`.
- فرم Admin فقط انتخاب نقش مجاز، والد، اعتبار و تنظیمات ضروری را نشان دهد؛ API خارجی در فرم جداگانه Owner-only باشد.
- نمایش tree یا breadcrumb سلسله‌مراتب.
- دکمه «ساخت زیرادمین» فقط برای Owner و Super Admin.
- نمایش سه مقدار اعتبار: کل، واگذارشده، قابل‌واگذاری.
- عملیات «واگذاری اعتبار» و «پس‌گرفتن اعتبار» با تأیید نهایی.
- فرم ساده پیش‌فرض و تنظیمات تخصصی در بخش پیشرفته.
- Owner کل درخت؛ Admin فقط subtree خودش را دریافت کند.
- منوهای Node، Core، تنظیمات سراسری، آمار کل پنل و reset کل برای غیر Owner هم در UI حذف و هم در backend ممنوع شوند.
- داشبورد غیر Owner با خلاصه حساب و activity scope‌شده جایگزین شود.
- در فرم Admin، «اجازه تمدید» و در صورت فعال‌بودن «تعداد تمدید» نمایش داده شود؛ نام سهمیه تمدید از سهمیه ساخت جدا و غیرمبهم باشد.
- mode حسابداری Admin با عنوان «مصرف اعتبار بر اساس حجم تخصیص‌یافته» نمایش داده شود؛ آمار واقعی کل پنل با آن ترکیب نشود.
- دکمه «غیرفعال‌سازی همه کاربران» با scope، شمار هدف، تأیید و progress عملیات اضافه شود.
- بخش Owner برای Planهای پیش‌فرض و بخش Super Admin مجاز برای Planهای شاخه خودش اضافه شود.
- فرم `PLAN_ONLY` فقط انتخاب plan و فیلدهای حداقلی را نشان دهد؛ فیلدهای دستی حذف شوند.
- صفحه User در حالت `PLAN_ONLY` دکمه و dialog مستقل «تمدید با Plan» داشته باشد.
- Admin معلق فقط صفحه read-only دلیل تعلیق، زمان، مانده و راه رفع را ببیند.

## مراحل پیاده‌سازی

- [x] مرحله ۰ — ثبت نیازمندی، بررسی ساختار فعلی و ایجاد نقشه راه
- [x] مرحله ۱ — قفل‌کردن قرارداد سه نقش، API خارجی، scope کاربر، داشبورد حساب، اعتبار و باگ‌های اعلامی
- [ ] مرحله ۲ — طراحی migration، backup و rollback روی clone واقعی MySQL؛ تست SQLite کامل، clone واقعی MySQL باقی مانده
- [x] مرحله ۳ — افزودن schema نقش‌ها، سلسله‌مراتب، Owner singleton، closure table، ledger و token API
- [x] مرحله ۴ — افزودن service مرکزی role/scope و queryهای subtree
- [x] مرحله ۵ — محدودکردن endpointهای User، Admin، audit، Device Limit، System، Node، Core و WebSocketها
- [ ] مرحله ۶ — رفع `BUG-DVL-003`، سپس `BUG-ADM-001` و `BUG-USR-002` با test بازگشتی و شواهد DB/Core/Node/UI
- [x] مرحله ۷ — پیاده‌سازی مجوز تمدید، حسابداری created traffic، قطع خودکار و عملیات گروهی chunked
- [x] مرحله ۸ — افزودن schema و service Plan، وراثت، version و assignment
- [x] مرحله ۹ — پیاده‌سازی انتقال و reclaim اعتبار با locking و idempotency
- [x] مرحله ۱۰ — افزودن CLI تعیین/تعویض Owner، API خارجی Owner-only و حذف sudo از API و پنل
- [x] مرحله ۱۱ — مهاجرت امن sudoها، Adminها، تنظیمات قبلی و Userهای بدون مالک؛ template قدیمی بدون حذف حفظ می‌شود و Plan خودکار ساخته نمی‌شود
- [x] مرحله ۱۲ — رابط tree، سه نقش، Planها، ساخت/تمدید User، مدیریت اعتبار و داشبورد خلاصه حساب
- [ ] مرحله ۱۳ — تست امنیت، هم‌زمانی، MySQL، performance، migration و عملیات گروهی در مقیاس بالا
- [ ] مرحله ۱۴ — staging، backup، rollout مرحله‌ای، مشاهده metrics و rollback drill
- [ ] مرحله ۱۵ — انتشار نسخه immutable و ثبت دستور نصب/rollback

## آزمون‌های اجباری

- Owner همه شاخه‌ها را می‌بیند.
- Super Admin فقط subtree خودش را می‌بیند.
- Admin فقط Own Users خودش را می‌بیند.
- Super Admin والد Userهای Descendant را مدیریت می‌کند.
- صاحب مستقیم User و Adminهای بالاسری مجاز بتوانند آن User را فعال، غیرفعال، reset، revoke، ویرایش و حذف کنند.
- پاکسازی حساب‌ها فقط روی subtree مجاز اثر بگذارد و شاخه دیگر را تغییر ندهد.
- فرزند به والد، sibling و شاخه دیگر دسترسی ندارد.
- payload دست‌ساز مجوز فراتر از والد نمی‌دهد.
- فقط Owner به routeهای Node، Core، Xray، WebSocket لاگ و reset مصرف کل پنل دسترسی دارد.
- پاسخ System برای غیر Owner هیچ آمار سراسری، پهنای‌باند یا مشخصات زیرساختی نشت نمی‌دهد.
- API خارجی برای Super Admin و Admin بعد از migration خاموش است.
- فقط Owner API خارجی را فعال یا لغو می‌کند؛ Super Admin حتی برای فرزند خودش نیز نمی‌تواند.
- خاموش‌بودن API خارجی، session پنل و endpointهای scope‌شده موردنیاز UI را خراب نمی‌کند.
- revoke دسترسی API همه tokenهای خارجی فعال Admin را بی‌اعتبار می‌کند.
- audit غیر Owner فقط فعالیت‌های خودش و subtree را نشان می‌دهد؛ Owner audit سراسری دارد.
- Admin بدون `renewal_enabled` در UI و API نتواند User را تمدید کند.
- تمدید هم‌زمان با آخرین سهمیه فقط یک‌بار موفق شود و شمارنده منفی نشود.
- retry یک تمدید plan-based اعتبار یا سهمیه را دوباره مصرف نکند.
- حسابداری `created_traffic` حجم تخصیص‌یافته ساخت و تمدید را ثبت کند و حذف/reset آن را برنگرداند.
- اتمام تاریخ یا اعتبار حجم Admin، حساب و Userهای scope او را قطع کند؛ پرشدن `max_users` فقط ساخت جدید را متوقف کند.
- resume فقط Userهای غیرفعال‌شده توسط همان suspension event را بازیابی کند.
- غیرفعال‌سازی همه کاربران یک Admin یا subtree در ۱۰٬۰۰۰ و ۱۰۰٬۰۰۰ User به‌صورت batch و قابل‌ادامه تست شود.
- Admin در حالت `PLAN_ONLY` نتواند با payload دستی volume، expiry، limit یا inbound را override کند.
- Super Admin بدون `can_manage_plans` نتواند plan بسازد و plan والد را تغییر دهد.
- plan جدید از سقف‌های Parent عبور نکند و plan archived برای ساخت/تمدید جدید قابل‌استفاده نباشد.
- تغییر version plan روی Userهای قبلی اثر retroactive نگذارد.
- تست بازگشتی `BUG-ADM-001` limit را در درخواست‌های عادی و هم‌زمان تأیید کند.
- تست بازگشتی `BUG-USR-002` قطع واقعی User را در DB، Core محلی و Node نشان دهد.
- تست بازگشتی `BUG-DVL-003` observation دو IP را از collector تا DB، API و UI ردیابی و source node/time را تأیید کند.
- تست دسترسی IP: Owner مقدار کامل، Admin مجاز مقدار mask‌شده و نقش بدون scope هیچ داده‌ای از شاخه دیگر نبیند.
- ساخت چرخه در hierarchy رد می‌شود.
- دو انتقال هم‌زمان موجب خرج دوباره اعتبار نمی‌شوند.
- درخواست تکراری با یک idempotency key دوباره شارژ نمی‌شود.
- reclaim بیشتر از مانده فرزند رد می‌شود.
- migration sudoهای فعلی هیچ Admin یا User را حذف نمی‌کند.
- Userهای بدون مالک به Owner متصل می‌شوند.
- بدون Owner، فعال‌سازی hierarchy شکست امن دارد.
- query subtree در ۱۰٬۰۰۰ و ۱۰۰٬۰۰۰ Admin با `EXPLAIN ANALYZE` بررسی می‌شود.
- query User در میلیون‌ها ردیف از index مناسب استفاده می‌کند و full table scan ندارد.

## قرارداد اجباری سازگاری Update

برای Stageهای 7 تا 13، نسخه جدید باید با دستور update موجود Marzban از baseline
نصب `v4.9.8` و schema فعلی پروژه روی MySQL 8.x / InnoDB بالا بیاید. موفق‌بودن فقط
روی DB توسعه یا SQLite قابل قبول نیست. بندهای legacy زیر به‌عنوان قرارداد تاریخی
و رفتار پیاده‌شده حفظ می‌شوند، اما ماتریس hypothetical production legacy توسعه
نمی‌یابد مگر dependency واقعی current working tree آن را لازم کند.

### ماتریس الزامی آزمون Upgrade

- نصب تازه/خالی `v4.9.8` تا Alembic head جدید روی MySQL واقعی.
- DB در head فعلی پروژه هنگام شروع Stage تا head جدید.
- DB با DDL جزئی یا migration نیمه‌اجراشده، فقط برای migrationهای جدید Stageهای
  باقی‌مانده که recovery آن‌ها واقعاً لازم است.
- اجرای دوباره همان migration پس از قطع سرویس یا برق.
- حفظ ID، ownership، credit، usage، ledger، refund و scope موجود در dataset نماینده
  current schema؛ بدون ساخت population تاریخی فرضی.
- اجرای image rollback روی schema جدید، هرجا سیاست rollout فعلی آن را لازم می‌کند؛
  rollback فعلی migration دیتابیس را downgrade نمی‌کند.
- PostgreSQL/TimescaleDB و validation متقاطع DB خارج از دامنه فعلی‌اند.

release تا موفقیت همه حالت‌های مرتبط بالا منتشر نشود. SQLite جایگزین هیچ evidence
migration/concurrency/query-plan نیست.

### الگوی migration

الگو همیشه `expand -> backfill -> verify -> contract` باشد:

1. ستون‌های جدید ابتدا nullable یا دارای default سازگار و جدول‌های جدید افزایشی باشند.
2. کد مدتی schema قدیم و جدید را بخواند و در صورت نیاز dual-write انجام دهد.
3. backfill در batch محدود و قابل‌ادامه اجرا شود؛ آخرین cursor در لاگ ثبت شود.
4. invariantها و reconciliation کامل بررسی شوند.
5. حذف ستون قدیمی، rename، narrow type یا constraint سخت در همان release ممنوع باشد.
6. cleanup فقط در release بعدی و پس از پایان پنجره rollback انجام شود.

این الزام حیاتی است، چون اسکریپت فعلی هنگام rollback فقط image قبلی را برمی‌گرداند و migration دیتابیس را downgrade نمی‌کند. پس image قبلی باید با schema گسترش‌یافته جدید همچنان کار کند.

### راهکار داده‌های قدیمی بدون Parent یا Owner

migration اولیه نباید برای ساخت hierarchy به داده‌ای که در نسخه قدیمی وجود نداشته تکیه کند:

1. ستون‌های role و parent ابتدا nullable افزوده شوند و `hierarchy_enabled=false` بماند.
2. اگر Owner هنوز با دستور سرور تعیین نشده، update کامل شود و برنامه در compatibility mode با رفتار قدیمی `is_sudo` بالا بیاید؛ migration یا health check شکست نخورد.
3. فرمان زیر backfill را داخل یک transaction انجام دهد:

```bash
marzban set-owner <username>
```

4. Admin انتخاب‌شده Owner شود.
5. sudoهای قدیمی دیگر Super Admin و فرزند مستقیم Owner شوند.
6. Adminهای معمولی قدیمی بدون Parent معتبر، Admin و فرزند مستقیم Owner شوند.
7. رابطه معتبر موجود حفظ شود؛ Parent مفقود، ناموجود، self-reference یا چرخه به Owner منتقل و با reason code جدا ثبت شود.
8. User دارای `admin_id=NULL` به Owner متصل شود. User دارای `admin_id` معتبر جابه‌جا نشود.
9. هیچ Admin، User، credit، usage، ledger، template، node یا audit حذف نشود.
10. پس از تأیید دقیق یک Owner، نبود orphan/cycle، closure consistency و reconciliation داده، `hierarchy_enabled=true` شود.
11. اگر هر invariant شکست خورد، transaction backfill rollback، compatibility mode حفظ و دلیل دقیق برای اصلاح نمایش داده شود؛ update برنامه خراب نشود.

reason codeهای حداقلی برای لاگ parent:

- `existing_valid_parent_preserved`
- `legacy_sudo_attached_to_owner`
- `legacy_admin_missing_parent_attached_to_owner`
- `missing_parent_attached_to_owner`
- `self_parent_attached_to_owner`
- `cycle_broken_attached_to_owner`
- `null_user_owner_attached_to_owner`

### گزارش اجباری به کاربر هنگام هر تغییر DB

هر لاگ پیشرفت migration باید اطلاعات زیر را در حد مرتبط با baseline فعلی نشان دهد.
فیلدهای legacy/backfill که dependency واقعی ندارند برای Stageهای 7 تا 13 `N/A`
ثبت می‌شوند و برای پرکردن آن‌ها dataset فرضی ساخته نمی‌شود:

- source tag/commit و target tag/commit.
- source Alembic head و target head.
- engine و نسخه DB.
- مسیر backup، زمان، حجم/checksum و نتیجه restore test.
- سناریو: fresh، existing data، legacy data یا partial migration.
- تعداد ردیف قبل/بعد جدول‌های درگیر.
- تعداد Parentهای حفظ‌شده و ساخته‌شده به تفکیک reason code.
- Owner انتخاب‌شده، sudoهای تبدیل‌شده، Adminهای متصل‌شده و Userهای بدون مالک.
- بررسی حفظ IDها، ownership، credit، usage، ledger و نبود orphan/cycle.
- تست‌های اجراشده، خطاها، ریسک عملیاتی و سازگاری image rollback.
- نقطه دقیق ادامه و فرمان بعدی.

## ریسک migration و rollback

- پیش از migration از MySQL و فایل‌های تنظیمات backup گرفته شود.
- migration ابتدا روی clone یا staging با حجم واقعی اجرا شود.
- schema افزایشی باشد؛ ستون‌های قدیمی `is_sudo` در release اول حذف نشوند.
- یک feature flag حالت hierarchy را کنترل کند.
- rollback برنامه با خاموش‌کردن feature flag ممکن باشد؛ داده hierarchy و ledger حذف نشود.
- rollback نباید انتقال‌های مالی ثبت‌شده را معکوس یا پاک کند.
- پس از rollout، شمار Adminها، Userهای بدون مالک، closure rowها، مجموع اعتبار و اختلاف ledger کنترل شود.
- migration جدید قبل از release روی baseline نصب `v4.9.8`، schema فعلی پروژه و DB
  خالی MySQL اجرا شود؛ snapshot قدیمی‌تر فقط با dependency واقعی current لازم است.
- recovery از MySQL partial DDL اجباری باشد؛ اتکا به rollback تراکنشی DDL ممنوع.
- تا وقتی backfill Owner/Parent کامل نشده، compatibility mode و `is_sudo` قدیمی حفظ شود.
- constraintهای سخت Parent و حذف ستون‌های قدیمی تا release بعد از پایان پنجره rollback به‌تعویق بیفتند.

## تصمیم‌های باقی‌مانده پیش از شروع کدنویسی

- [x] تأیید سه نام نهایی `Owner`، `Super Admin` و `Admin`
- [x] تأیید دستور نهایی `marzban set-owner <username>`
- [x] تأیید اینکه مرحله اول فقط اعتبار حجم را منتقل کند
- [x] تعیین مجوز انتقال یک subtree بین دو والد: فقط Owner در نسخه اول
- [x] تعیین رفتار Adminهای env در نصب‌های قدیمی: تبدیل به رکورد DB هنگام `set-owner` و حذف bypass فقط پس از backfill موفق
- [x] تعیین حداکثر عمق منطقی برای محافظت عملیاتی: `64`؛ مدل DB محدودیت فنی عمق ندارد
- [x] داشبورد غیر Owner شامل تفکیک Own Users و subtree باشد و هیچ آمار کل پنل یا زیرساخت نشان ندهد
- [x] مدیریت Node، Core، Xray و reset کل پنل فقط Owner باشد
- [x] API خارجی غیر Owner پیش‌فرض خاموش و فقط توسط Owner قابل‌مدیریت باشد
- [x] تأیید تفسیر «API خارجی»؛ session و endpointهای داخلی پنل scope‌شده باقی می‌مانند
- [x] ثبت اولیه `BUG-ADM-001`، `BUG-USR-002` و `BUG-DVL-003`
- [x] تعیین اینکه `BUG-ADM-001` مربوط به `concurrent_user_limit` و تشخیص IP/دستگاه اضافه است
- [ ] دریافت log collector و نمونه User/Node برای `BUG-DVL-003`
- [ ] دریافت مراحل بازتولید، username آزمایشی و وضعیت Core/Node برای `BUG-USR-002`
- [x] تأیید اینکه Admin معلق فقط داشبورد read-only دلیل تعلیق را ببیند
- [x] تأیید اینکه پایان اعتبار/تاریخ Super Admin تمام subtree را قطع کند
- [x] تعیین planهای پیش‌فرض اولیه: migration هیچ Plan خودکاری نمی‌سازد؛ Owner صریحاً ایجاد می‌کند
- [x] تعیین سیاست تمدید: strategy در version Plan؛ پیش‌فرض جایگزینی حجم و زمان از `max(now, current_expire)`
- [x] تعیین دسترسی Plan: allowlist فرزند؛ انتشار subtree گزینه مستقل با پیش‌فرض خاموش

## نقطه دقیق ادامه

> [!todo] انتشار پایدار `v5.1.0` (`2026-09-04`)
> مراحل `0` تا `7` نقشه‌راه اجرای Codex کامل‌اند. MySQL 8 migration matrix،
> backup/restore، سناریوی زنده Master + Node A + Node B، backend با
> `275 passed, 9 skipped` و frontend production build پاس شدند. نقطه ادامه:
> commit و tag تغییرناپذیر `v5.1.0`، انتظار برای CI/GHCR/GitHub Release، سپس smoke
> test نصب و update از artifact منتشرشده.

> [!todo] مرحلهٔ `2` نقشه‌راه اجرای Codex (`2026-09-04`)
> مرحلهٔ `1` کامل است. Host ID اکنون در edit حفظ می‌شود و commit داخل loop حذف شده؛
> Impact Analysis read-only تعداد Plan/version/User و Plan نامعتبر را گزارش می‌کند؛
> mutation بدون تصمیم صریح با قرارداد فارسی `409` رد می‌شود و DB تغییر نمی‌کند؛ regression
> network-only Plan revision شرایط مالی قبلی را حفظ می‌کند و migration افزایشی
> `d3a5c7e9f102` Host تاریخی را برای runtime نگه می‌دارد. actionها اتمیک متصل‌اند؛
> `future_only` snapshot جاری را نگه می‌دارد و `detach`
> کاربران فعال را با assignment نوع `network_sync` منتقل می‌کند؛ `10 passed`. نقطهٔ ادامه:
> Modal فارسی Impact Analysis کامل و TypeScript/UX contract پاس شد. نقطهٔ ادامه: `2.4`،
> یکسان‌سازی Host scope در User API، Subscription، QR و Copy Config. Graphify دوباره scan نمی‌شود.

> [!success] مرحلهٔ `1` نقشه‌راه اجرای Codex (`2026-09-04`)
> password از مسیر report ورود حذف شد؛ self-edit فیلدهای تجاری Admin در backend با
> `403 self_commercial_edit_forbidden` بسته شد؛ تمام API/UI مربوط به Device Limit
> Owner-only شد؛ activation عادی هنگام penalty فعال با `403 device_limit_penalty_active`
> مسدود و restore وضعیت قبلی فقط در flow Owner انجام شد. تست backend هدفمند، قرارداد UI،
> TypeScript و compile پاس شدند. schema/migration/dependency/commit/push/tag/release/deploy
> انجام نشد. نقطهٔ ادامه: مرحلهٔ `2 — Host / Inbound / Plan Synchronization`.

> [!success] مرحلهٔ `0` نقشه‌راه اجرای Codex (`2026-09-04`)
> workspace، branch، HEAD، tag/release/GHCR، migration head و اسناد تحویلی تطبیق داده شدند.
> baseline جاری `v5.0.0-rc.13@69e105fcebf627f0b9dfe588a9f7e3205767b01a`،
> migration head برابر `c2f4a8d6e913` و rollback تأییدشده
> `v5.0.0-rc.11@04048b90ce27fd77d0ca3f936faca26da932ef90` است. Graphify فقط برای
> navigation/dependency روی HEAD تازه شد. findings در
> [[CODEX_IMPLEMENTATION_CHECKPOINT_FA]] به چهار دستهٔ قطعی، سند منقضی، نیازمند
> بررسی زنده و نیازمندی محصول تفکیک شدند. هیچ feature، schema، migration، dependency،
> commit، push، tag، release یا deploy انجام نشد. نقطهٔ ادامه: مرحلهٔ `1`؛ فرمان دقیق
> `مرحله 1 را شروع کن`.

> [!todo] حذف نمایش روش ساخت کاربر و انتشار سالم `v5.0.0-rc.13` (`2026-08-26`)
> کاربر صریحاً حذف «روش ساخت کاربر» از فرم ساخت و ویرایش Admin و انتشار نسخهٔ
> immutable جدید را خواست. backend از `billing_mode` مقدار canonical را تعیین می‌کند:
> `USED_TRAFFIC=FREE_FORM` و `ALLOCATED_TRAFFIC/USER_CREDIT=PLAN_ONLY`. انتخاب یا
> نمایش دستی از فرم حذف شود، اما enforcement و payload سازگار باقی بماند. سپس build
> نسخه‌دار، تست هدفمند UI/backend/migration/release، Graphify، review کامل diff و
> انتشار GitHub/GHCR انجام شود؛ `marzban update` و دریافت تازهٔ installer واقعاً
> بررسی شوند. baseline شبکه: remote tag `v5.0.0-rc.11@04048b9` و Latest پایدار
> `v4.9.8`؛ نسخهٔ بعدی فقط پس از گیت محلی منتشر شود.

> [!success] لانچر تک‌دستوری Dev محلی (`2026-08-26`)
> اسکریپت PowerShell ایزوله با MySQL آزمایشی روی `127.0.0.1:33079`، Alembic، seed
> تکرارپذیر Owner/Admin/User/Plan، Backend واقعی با Xray و Vite HMR اجرا شد. probe
> بدون خطای image، pull صریح MySQL، Dockerfile مخصوص CRLF ویندوز، context بدون
> artifactهای محلی و root درست Vite اعمال شد. seed علاوه بر ساخت روش canonical
> `chacha20-ietf-poly1305`، داده نمونه قدیمی را هم idempotent اصلاح می‌کند؛ در نتیجه
> `/api/users` دیگر ResponseValidationError ندارد. ورود Owner و سه Admin، MySQL
> healthy، Frontend=`200`، Owner API، فهرست چهار Admin و شش User و Browser داخلی
> بدون console error پاس شد. production، schema، migration، dependency و release
> تغییر نکرد. نقطه ادامه: Dev روشن بماند؛ تغییر source با Save از Vite HMR دیده شود.

> [!todo] ساده‌سازی مدیر و دسترسی‌های Plan-only (`2026-08-25`)
> درخواست و تصمیم‌های قطعی در [[ADMIN_SIMPLIFICATION_HANDOFF_FA]] ثبت شد. ادامه از نوشتن
> تست‌های بازگشتی و migration افزایشی نقش آغاز شود. working tree دارای تغییرات قبلی
> Modal و fail-closed است و نباید revert شود. `v5.0.0-rc.11@04048b9` baseline محلی است؛
> GitHub prerelease `rc.11` و Latest پایدار `v4.9.8` تأیید شدند، اما `git ls-remote`
> به‌علت DNS و GHCR digest به‌علت نبود `read:packages` ناموفق بود. پیاده‌سازی و تست
> محلی ادامه یابد؛ commit/push/tag/release/deploy تا تأیید دوباره و دستور صریح ممنوع.

> [!success] بازگردانی فرم Admin به Modal وسط‌چین (`2026-08-25`)
> تصویر production با source و tag `v5.0.0-rc.11` تطبیق داده شد: خرابی cache یا
> updater نیست. `AdminFormDrawer.tsx` عمداً Chakra `Drawer size="full"` با ارتفاع
> `100dvh` و عرض desktop برابر `940px` می‌سازد و contract در
> `test-admin-ux.cjs` نیز Modal را ممنوع کرده است؛ بنابراین CI ظاهر غلط را صحیح فرض
> کرده بود. wrapper به `Modal size="5xl"` با `maxH="calc(100dvh - 24px)"`، scroll
> داخلی، footer ثابت و دکمه بستن سمت مقابل عنوان برگشت؛ تمام fieldها، permissionها،
> APIها و business logic حفظ شدند. Browser یک loop موجود در deep-link
> `#/admins/?create=1` را نیز آشکار کرد؛ dependency ناپایدار `formDisclosure` با callback
> پایدار جایگزین شد. desktop=`1440x900` و mobile=`375x812` هر دو مرکز دقیق، حاشیه
> `12px` و بدون overflow افقی‌اند؛ contractها، TypeScript، build production و rebuild
> بایت‌به‌بایت=`PASS`. نقطه ادامه: در صورت درخواست صریح، bump نسخه و committed build،
> regression، commit/push/tag/GHCR/Release immutable بعدی؛ بدون deploy.
> هیچ push، tag، release یا deploy بدون درخواست صریح جدید انجام نشود.

> [!warning] اصلاح `PLAN_ONLY` و بازیابی فهرست User برای `v5.0.0-rc.11` (`2026-08-25`)
> baseline شبکه بازتأیید شد: `v5.0.0-rc.10@7b6aaf27e25bbd9b8740d71d4dd971796d987695`،
> Actions run `32795972592=success`، GitHub prerelease موجود و GHCR digest برابر
> `sha256:1c92fd3bc0048324c0d824ab5b0b3a34bc79b46d5f79fa785ec754d295a7fd18` است؛
> Latest پایدار GitHub همچنان `v4.9.8` است. بازتولید منبع نشان داد `UserDialog` برای
> `PLAN_ONLY` payload ناقص بدون proxy می‌سازد؛ در حالت compatibility، `crud.create_user`
> رکورد را پیش از `UserResponse` commit می‌کند، serialization با الزام proxy به HTTP 500
> می‌رسد، retry به 409 می‌رسد و همان رکورد بدون proxy تمام پاسخ‌های `/api/users` را 500
> می‌کند. اصلاح کامل شد: backend ساخت بدون proxy را پیش از commit با HTTP 422 رد می‌کند
> و خواندن رکورد خراب موجود را برای بازیابی و حذف اپراتوری تحمل می‌کند؛ UI تا دریافت
> policy fail-closed است و برای `PLAN_ONLY` فقط مسیر `/plans/` را نشان می‌دهد. full
> regression=`226 passed, 9 skipped`، contractهای پنل و TypeScript=`PASS`، build نهایی
> `index.36f50bb0.js` با rebuild بایت‌به‌بایت=`PASS` و Graphify=`4464/11445/467` است.
> نقطه ادامه: manifest محدود، commit/push/tag، MySQL CI و تطبیق GHCR/Release immutable
> `v5.0.0-rc.11`؛ بدون deploy.

> [!warning] آماده‌سازی انتشار immutable `v5.0.0-rc.10` پس از گیت `rc.9` (`2026-08-25`)
> بازتولید شد: validation داخل `install_command` هنوز prerelease را رد می‌کند؛
> `latest` از endpoint/تگ stable-only استفاده می‌کند؛ نصب پس از health وارد follow
> بی‌پایان log می‌شود؛ و CI با lockfile قدیمی‌تر از dependencyهای بیلد محلی کار
> می‌کند. همچنین مسیر ساخت اولیه Owner باید non-interactive و قابل‌آزمون شود.
> اصلاح محدود انجام شد: latest به جدیدترین release غیردرفت resolve می‌شود، install/
> update/script/files/image همگی ref دقیق دارند، نصب پس از health برمی‌گردد، bootstrap
> امن Owner اضافه شد، optional promptهای ساخت Admin حذف شدند، dependencyهای واقعی
> dashboard قفل و build با Node `20.19.5` تولید شد؛ cache key زمانی locale با VERSION
> deterministic جایگزین شد و CI اختلاف build committed را رد می‌کند. خطای
> `selectionStart` با حفظ NumberInput و DOM `text + decimal inputMode`
> رفع شد. APIهای User/Admin، schema، migration، query/index و accounting تغییر نکردند.
> `rc.9@559b4cd` در هر سه گیت MySQL موفق بود اما parity بایت‌های minifier بین
> Windows/Linux را رد کرد و image/Release نساخت؛ tag immutable حفظ شد. در `rc.10`
> CI source را در `/tmp` build می‌کند، committed dashboard را تغییر نمی‌دهد و Docker
> دقیقاً همان build ثبت‌شدهٔ محلی را حمل می‌کند. نقطهٔ ادامه: گیت محلی، commit/push/tag
> `v5.0.0-rc.10`، انتظار CI MySQL/build/image/release؛ هیچ deploy اجرا نشود.

> [!warning] انتشار immutable `v5.0.0-rc.8` — گیت parity updater (`2026-08-25`)
> `v5.0.0-rc.7@a4045b87e89f33d62c79f00f837db9ac62d8558f` با CI، MySQL، GHCR
> و GitHub Release موفق منتشر شد؛ اما بازبینی نهایی updater نشان داد regex قدیمی فقط
> tag پایدار را به‌عنوان ref اسکریپت می‌پذیرد و برای tagهای `rc` پس از pull ایمیج دقیق،
> اسکریپت را از `master` می‌گیرد. `rc.7` immutable و دست‌نخورده می‌ماند. اصلاح فقط
> پذیرش SemVer prerelease در `marzban_script_ref` است و هیچ application/API/UI/DB/
> migration/dependency تغییری ندارد. `.codex/`، `graphify-out/`، `design-system/`،
> `.graphifyignore` و دو حذف نامطمئن مستندات خارج انتشار می‌مانند. نقطهٔ ادامه:
> اجرای release/update contract و regression؛ بازبینی diff/manifest/secret؛ commit و
> push branch؛ tag annotated `v5.0.0-rc.8`؛ انتظار کامل CI؛ سپس تطبیق commit/tag/
> Release و digest دو tag ایمیج. هیچ deploy اجرا نشود.

> [!success] برش بازطراحی داده‌محور فهرست Admin — کامل (`2026-08-24`)
> صفحهٔ `Admins` طبق مرجع فشردهٔ مشکی–طلایی کاربر بازطراحی شد، بدون افزودن
> summary، endpoint یا دادهٔ تکراری. ردیف desktop فقط چهار گروه دارد: هویت و وضعیت،
> نوع دسترسی و کاربران، اعتبار، عملیات permission-aware. موبایل همان داده را به کارت
> فشرده و بدون جدول افقی تبدیل می‌کند. جست‌وجو، فیلترهای جمع‌شونده، انتخاب گروهی،
> pagination، جزئیات، ویرایش، حذف، Freeze/Resume/Activate، Trial reset و ledger
> افزایش/کاهش اعتبار حفظ شدند. contract، TypeScript، Vite، Browser در
> `375/768/812x375/1024/1440` و Graphify همگی PASS شدند. API/schema/migration/
> query/index/accounting/permission/version/install/update بدون تغییر. نقطهٔ ادامه:
> این برش کامل است؛ بدون commit/push/tag/release/deploy.

> [!success] برش بازطراحی داشبورد — کامل (`2026-08-24`)
> داشبورد بر پایهٔ مرجع مشکی–طلایی کاربر بازطراحی شد، اما فقط داده‌های واقعی و
> غیرتکراری نمایش داده می‌شوند. منابع قطعی این برش عبارت‌اند از aggregateهای
> scope-aware در `/dashboard/overview`، وضعیت و اعتبار حساب در `/account/summary`،
> پنج فعالیت آخر از cursor endpoint موجود `/account/activity?limit=5` و منابع واقعی
> سرور در `/system` فقط برای Owner. نمودار نوع اعتبار فقط وقتی بیش از یک mode دارای
> داده باشد نمایش داده می‌شود؛ برای حساب تک‌حالته، خلاصهٔ همان مدل اعتبار جایگزین
> می‌شود. API، schema، migration، query، index، accounting، permission، version،
> install و update در این برش تغییر نکردند. جزئیات تحلیلی در موبایل پیش‌فرض بسته
> است و Dashboard دیگر summaryهای تکراری را mount نمی‌کند. contract، TypeScript،
> build، Browser در `375/768/812x375/1024/1440` و ماتریس Owner/Super/Admin همگی
> PASS شدند. نقطهٔ ادامه: این برش کامل است؛ بدون commit/push/deploy/release.

در `2026-08-24` منوی عملیات سریع داشبورد اصلاح شد. trigger با مختصات فیزیکی در
گوشهٔ چپ قرار گرفت و در Browser با کنترل branding هم‌پوشانی نداشت. «فهرست کاربران»،
«مدیریت ادمین‌ها»، لینک عمومی «پلن‌ها» و تنظیمات تکراری حذف شدند. «ساخت ادمین» فقط
با `can_create_admins` و «ساخت پلن» فقط برای Owner یا `can_manage_plans` نمایش داده
می‌شوند؛ فرم واقعی Admin Drawer و فرم Plan با همان validation شبکه داخل Dashboard
باز می‌شوند و URL بدون navigation/reload ثابت می‌ماند. ماتریس preview برای Owner،
Super Admin و Admin محدود، UI/permission/inbound/TypeScript/build/Browser/console
همگی PASS شدند. نقطه ادامه: برش کامل است؛ بدون backend/schema/accounting/version و
کار بعدی فقط با دستور صریح جدید شروع شود.

در `2026-08-24` گزینه‌های پیشرفته و وضعیت `DISABLED` اصلاح و کامل شد. علت نمایش
کلیدهای انگلیسی، استفادهٔ مستقیم UI از نام فیلدهای policy به‌جای کلیدهای ترجمهٔ
موجود بود. هر پنج محدودیت عملیات مستقل از نوع اعتبار باقی ماندند: ساخت/حذف/reset/
revoke کنترل مجوز عملیاتی‌اند و منع حجم نامحدود در `PLAN_ONLY` نیز Plan نامحدود را
fail-closed می‌کند. `disabled_branch` فقط fixture دیتای preview است؛ مسیر
فعال‌سازی صریح برای Owner/والد مجاز اضافه شد و فقط account status را تغییر می‌دهد؛
User، credit، Plan و accounting دست‌نخورده می‌مانند. «والد» به «زیرمجموعهٔ» تغییر
کرد. targeted/full/UI/TypeScript/build/Browser/Graphify همگی PASS شدند. نقطه ادامه:
برش کامل است؛ بدون schema/migration/version/dependency و کار بعدی فقط با دستور
صریح جدید شروع شود.

در `2026-08-24` رگرسیون رفع فریز رابط بررسی شد: UI فقط وجود
`active_owner_freeze_event_id` را می‌سنجد، پس Admin با `account_status=SUSPENDED`
و فریز دستی دکمه ندارد. قرارداد موجود backend دو مسیر دارد: `unfreeze` برای رویداد
Owner subtree و `resume` برای suspension دستی. تست واقعی نشان داد suspension قدیمی
بدون event نیز از `resume` با `no_active_suspension` رد می‌شود. اصلاح محدود backend:
eventless suspension فقط وقتی شرط خودکار credit/expiry فعال نیست پاک می‌شود؛ eventهای
موجود و restoration snapshot دست‌نخورده ماندند. service/full/build/Browser همگی
PASS شدند و تست واقعی `frozen_branch: SUSPENDED -> ACTIVE` موفق بود؛ preview سپس
به حالت فریز اولیه بازگردانده شد. نقطه ادامه: این برش کامل است؛ بدون
schema/migration/accounting change و کار بعدی فقط با دستور صریح جدید شروع شود.

در `2026-08-24` پس از اصلاح cache فرم، فهرست Admin در preview با
`GET /api/admin-management` و HTTP 500 متوقف شد. علت قطعی، تقسیم بر صفر در
`_quota_summary_values` برای credit محدود و تمام‌شده با `limit=0` است؛ credit صفر
باید finite و exhausted بماند، اما درصد آن بدون تقسیم برابر `100` گزارش شود.
هم‌زمان اکشن محلی افزایش/کاهش اعتبار با همان endpointهای ledger موجود کنار Freeze
در desktop/mobile اضافه شد. تست رگرسیون zero-credit، UI contract، TypeScript/build،
full backend و Browser همگی PASS شدند؛ رفت‌وبرگشت واقعی `0.01 GB` نیز بدون تغییر
ماندهٔ نهایی موفق بود. نقطه ادامه: این برش کامل است؛ بدون
schema/migration/query/version change و کار بعدی فقط با دستور صریح جدید شروع شود.

در `2026-08-24` بررسی دو گزارش ذخیره‌نشدن `PLAN_ONLY` و دسته‌های Plan روی
baseline `agent/admin-hierarchy-v4.9.0@3ca44d4d60178caa0b9ad4dd4560a6f0704c512f`
شروع شد؛ tag نصب remote برابر `v5.0.0-rc.6@cee2c74ce520c503f9dd66847cc62aa93edd5062`
بازتأیید شد. API و DB preview مقادیر `user_creation_mode=PLAN_ONLY` و
`plan_category_ids=[1]` را پس از ذخیره درست برگرداندند؛ raw create برای
`admin_demo` با `403 plan_only` رد شد و create-from-plan شمار Own User را
`1 -> 2` تغییر داد و پس از حذف probe به `1` برگشت. علت رابط، نگه‌داشتن رکورد
قدیمی در cache فهرست `admin-management` پس از mutation است؛ پاسخ canonical
سرور در cache نوشته نمی‌شود و بازکردن سریع فرم مقدارهای پیش از ذخیره را نشان
می‌دهد. اصلاح نهایی: cache همان query بلافاصله با پاسخ canonical درخواست PUT
به‌روزرسانی شد و سپس invalidation قبلی نیز حفظ شد؛ بنابراین بازکردن فوری فرم، mode
و دسته‌های تازهٔ Plan را از رکورد قدیمی بازسازی نمی‌کند. تست frontend، backend،
build و Browser همگی PASS شدند؛ بدون schema/migration/API/accounting change و
بدون commit/push/tag/release/deploy. نقطه ادامه: برش اصلاح این دو باگ کامل است و
کار بعدی فقط با دستور صریح جدید شروع شود.

در `2026-08-24` Owner رفع کامل رگرسیون‌های دسترسی و اصلاح UX فهرست‌شده در
بازخورد مرورگر را تأیید کرد. baseline برابر
`agent/admin-hierarchy-v4.9.0@91461d7b1637589b8189b4fba4193fc8eb5f3849`
با working tree موجود است؛ tag تغییرناپذیر remote برابر `v5.0.0-rc.3` و
GitHub Release پایدار دارای نشان `Latest` برابر `v4.9.8` بازتأیید شد. Docker
محلی برای بازتأیید digest GHCR موجود نیست و publication همچنان ممنوع است.

نقطه ادامه دقیق این برش:

1. ابتدا تست رگرسیون برای ممنوعیت raw/free-form در `PLAN_ONLY`، reset سهمیه
   Trial و دلیل اجباری Freeze نوشته و رفتار فعلی ثبت شود.
2. منطق دسترسی API پیش از UI اصلاح شود؛ Admin فقط طبق mode صریح والد و Plan
   واگذارشده کاربر بسازد و UI نتواند محدودیت server-side را دور بزند.
3. صفحه Admin، User dialog، Dashboard، Device Limit و Audit Log به‌صورت برش‌های
   کوچک و مستقل فشرده و فارسی شوند؛ قراردادهای سالم قبلی حفظ شوند.
4. دیتای preview متنوع و قابل‌بازتولید ساخته شود؛ targeted، full regression،
   TypeScript، Vite، browser در `375/768/1024/1440` و Graphify update اجرا شوند.

هیچ commit/push/tag/release/deploy/publish و هیچ migration روی DB واقعی مجاز نیست.

در `2026-08-24` Owner اجرای کامل برش اصلاحی مدیریت Admin و Dashboard را تأیید کرد.
baseline محلی و remote برابر
`agent/admin-hierarchy-v4.9.0@91461d7b1637589b8189b4fba4193fc8eb5f3849`
و tag تغییرناپذیر `v5.0.0-rc.3` است. GitHub Release پایدار دارای
نشان `Latest` هنوز `v4.9.8` است. image
`ghcr.io/smorad3363/marzban:v5.0.0-rc.3` با `404` تأیید نشد؛ image
قابل‌بازگشت `v5.0.0-rc.2` با digest
`sha256:7a5437403c6a45f6abb2e4673b28de7c2f58855410e3564cbe2dc435604a77c6`
و `latest` با digest
`sha256:f0fb12952f4120705eb1be24d1f174be7f877023133c1d53c73441f24e683081`
از GHCR قابل دریافت‌اند.

قرارداد برش جدید:

- Owner هیچ محدودیت تجاری/سهمیه‌ای ندارد و تمام بخش‌های پنل را مدیریت می‌کند؛
  invariantهای امنیتی و حسابداری همچنان اجباری‌اند.
- ساخت Admin با دو مجوز مستقل `can_create_admins` و
  `can_delegate_admin_creation` و سهمیه قابل‌واگذاری کنترل می‌شود؛ فرزند هرگز از
  والد قدرتمندتر نمی‌شود.
- والد `USED_TRAFFIC` در ساخت فرزن باید صریحاً بین
  `USED_TRAFFIC` و `ALLOCATED_TRAFFIC` انتخاب کند؛ هیچ پیش‌فرضی مجاز نیست.
- والد `ALLOCATED_TRAFFIC` فقط فرزن همان نوع، والد `SEAT_CREDIT` فقط
  فرزن همان نوع و Admin نامحدود فقط فرزن نامحدود می‌سازد.
- Freeze تکی و گروهی، عملیات گروهی فشرده و mode-aware، فرم ساخت
  تک‌صفحه‌ای، تلفن اختیاری با قرارداد `09xxxxxxxxx`، اقدام سریع reset
  سهمیه Trial، و عنوان‌های روشن در UI لازم است.
- Dashboard براساس billing mode با KPI، chart و دسترسی سریع تطبیق می‌یابد.
  theme اختیاری مشکی–طلایی و branding هر Admin با logo اختیاری و
  SVG پیش‌فرض هماهنگ با theme اضافه می‌شود.

وضعیت اجرای برش در همان تاریخ:

- migration افزایشی `8b7d3e5f1a24` برای مجوز/سهمیه ساخت Admin، baseline
  سهمیه Trial، theme و branding اضافه شد؛ mode قدیمی فقط برای migration حفظ و
  از ساخت تازه پنهان شد.
- Owner از تمام quotaهای تجاری معاف است؛ Super Admin و Admin فقط طبق مجوز،
  سهمیه، نقش و resource والد فرزند می‌سازند. والد `USED_TRAFFIC` برای هر فرزند
  انتخاب صریح `USED_TRAFFIC` یا `ALLOCATED_TRAFFIC` دارد و delegation آن مصرف
  واقعی subtree را جایگزین نمی‌کند.
- فرم ساخت/ویرایش تک‌صفحه‌ای و فشرده شد؛ تلفن اختیاری `09xxxxxxxxx`، Freeze و
  reset Trial سریع، فیلتر role/mode/status و bulk mode-aware بدون دلیل اجباری
  اضافه شد.
- Dashboard تطبیقی با KPI، نمودار، دسترسی سریع، تاریخ شمسی/تعطیلی، theme
  مشکی–طلایی و لوگوی اختیاری با SVG پیش‌فرض آماده شد. خروجی Vite مستقیماً در
  `app/dashboard/build` ساخته می‌شود تا preview و image همان نسخه جدید را سرو کنند.
- برای queryهای پرتکرار settings دو index مرکب mode/status و aggregate ثابت
  subtree افزوده شد تا tree و dashboard به N+1 برنگردند.

نقطه ادامه دقیق: full regression نهایی، Graphify update، ثبت evidence محیط MySQL
و Browser و سپس تحویل preview محلی. MySQL زنده در این Windows موجود نیست؛ migration
واقعی production تا clone امن MySQL 8.x همچنان ممنوع است.
commit/push/tag/release/deploy/publish در این برش ممنوع است.


در `2026-08-23` یک برش اصلاحی پس از `v5.0.0-rc.2` با مجوز صریح Owner شروع شد:
ساده‌سازی متن‌های Admin/Dashboard، افزودن کنترل روشن افزایش/کاهش اعتبار به فرم
ویرایش ادمین و تعمیر فرمان عمومی `marzban set-owner`. baseline محلی و remote برابر
`agent/admin-hierarchy-v4.9.0@49c9e1ddeeb2cf2784d256420657a2350ca41fb7`
و tag متناظر `v5.0.0-rc.2` است؛ GitHub origin به
`https://github.com/smorad3363/Marzban.git` اشاره دارد و GHCR همین tag با digest
`sha256:7a5437403c6a45f6abb2e4673b28de7c2f58855410e3564cbe2dc435604a77c6`
قابل دریافت است. علت واقعی خرابی فرمان کوتاه در نسخه نصب‌شده‌ی fork تأیید شد و
میان‌بر در commit ثابت
`smorad3363/Marzban-scripts@4830af3566022502159935eeb8636f1af3148502`
اضافه و روی `master` منتشر شد؛ remote مستقل `upstream` نیز حفظ شده است. UI از
endpointهای موجود دفترکل برای افزایش/کاهش جداگانه اعتبار استفاده می‌کند و هیچ
schema، migration یا قاعده حسابداری تغییر نکرده است. tag تغییرناپذیر
`v5.0.0-rc.3@91461d7b1637589b8189b4fba4193fc8eb5f3849` منتشر شد، اما CI به‌علت
قرارداد تست قدیمی Stage 9 که هنوز `type="tel"` را فقط در `Admins.tsx` می‌جوید
شکست خورد؛ فیلد اکنون بدون حذف رفتار به `AdminFormDrawer.tsx` منتقل شده است.
نقطه ادامه: حفظ کامل rc.3 و دریافت مجوز Owner برای test-only fix و rc بعدی؛ بدون
deploy و بدون final `v5.0.0`.

### سابقه نقطه ادامه Stage 12

در `2026-08-23` مجوز Owner برای external action محدود Stage 12 و مقصد
`smorad3363/Marzban-scripts` دریافت شد، اما preflight تکرارشده هنوز `BLOCKED` است:
`gh auth status` کاربر authenticated ندارد، `GH_TOKEN/GITHUB_TOKEN` موجود نیست و
fork مقصد نیز هنوز وجود ندارد. upstream در HEAD
`24a772d297c7518dae7650b8f106419e73813cda` قابل دسترسی است. نقطه ادامه: login امن
GitHub به حساب `smorad3363` و تکرار preflight. طبق Gate صریح، Stage 13 شروع نشده است.
main Marzban commit/push/tag/release/deploy/publish ممنوع باقی ماند.

خلاصه Stage 9 حفظ‌شده: Admin
جدید phone اجباری دارد، فرم Admin برحسب billing mode تنظیم می‌شود و Discord در UI
موردنظر نمایش داده نمی‌شود. داشبورد جدید aggregateهای scope-aware، چهار billing mode،
مرز هفته با timezone صریح و query count محدود دارد. migration
`6d4f2a9c8e10` ستون nullable phone را برای سازگاری schema فعلی و دو index داشبورد
اضافه می‌کند؛ rollback واقعی MySQL نیز تست شده است. نقطه ادامه Stage 10 است، اما شروع
آن نیازمند دستور صریح جدید است. commit/push/tag/release/deploy/publish همچنان ممنوع است.

بهینه‌سازی governance برای Stageهای 7 تا 13 ثبت شده است: deployment هرگز production
نبوده، DB هدف فقط MySQL 8.x / InnoDB است، compatibility لازم `v4.9.8` و schema
فعلی حفظ می‌شود، و `LEGACY_COMPAT` بدون dependency واقعی گسترش پیدا نمی‌کند.

Stage 6 پس از اجرای migration واقعی MySQL، backend، UI، آزمون
هم‌زمانی آخرین Trial Quota، idempotency و regression به `PASS` رسید. Trial با
metadata صریح و immutable از کاربر تجاری جدا می‌شود؛ سهمیه مستقل Admin فقط یک‌بار
مصرف می‌شود و cleanup فقط از metadata، در scope مجاز و پس از preview استفاده
می‌کند. Trial نامحدود همچنان از حسابداری mode عبور می‌کند و برای
`ALLOCATED_TRAFFIC` محدود fail-closed است. نقطه دقیق ادامه: توقف پس از Stage 6؛
Stage 7 شروع نشده و فقط با دستور صریح جدید و بررسی prerequisiteهای خودش مجاز است.
commit/push/tag/release/publish/deploy انجام نشده و همچنان ممنوع است.

تعمیر Stage 3 روی branch `agent/admin-hierarchy-v4.9.0` آماده انتشار `v4.9.8` است. `MRZ-DL-004` اصلاح شد: parser فرمت‌های واقعی source در Xray `26.7.28` را بدون fallback به destination می‌خواند؛ diagnostics محدود و sudo-only اضافه شد؛ و رفتار threshold/handoff grace با آزمون قطعی پوشش داده شد. tag `v4.9.7` به‌علت contract قدیمی نسخه در CI منتشر نشد و طبق سیاست immutable جابه‌جا نشد. پروتکل resume: پس از Graphify update، diff review و انتشار، این Stage متوقف است؛ تا درخواست صریح Stage 4 هیچ مرحله دیگری شروع نشود. این release تغییر schema یا migration ندارد.

زمینه تاریخی قبلی: tag `v4.9.2` روی commit `ded182ec2f50b3fe553752947eff27be7912c83e` قرار داشت؛ GitHub Actions run `32196890824` موفق شد و digest ثبت‌شده GHCR برابر `sha256:c0fdbfb7c4af7b2360ca8718c83f20ccf4dca7534fa38becb550e81bd6096973` بود. این اطلاعات baseline فعلی نیست و برای release بعدی باید دوباره از remote/GHCR تأیید شود.

### گزارش DB برش foundation

- source: `v4.8.0@fd73e03d3dffff158f3354883224f5a4094de2d7`، Alembic head=`a41c8e7d5b92`.
- target فعلی: working tree روی همان commit، Alembic head=`e2a6c1f4b903`؛ هنوز commit جدید ساخته نشده است.
- engine آزموده‌شده: SQLite `3.53.1` برای fresh/legacy، extended schema، backfill renewal و partial-column rerun.
- engine باقی‌مانده: MySQL `8.0`؛ `MYSQL_TEST_URL`، Docker، Podman و WSL در این محیط موجود نیست. تلاش WinGet و دانلود مستقیم Oracle CDN با `403 Forbidden` شکست خورد؛ بنابراین `EXPLAIN ANALYZE`، metadata-lock و partial DDL واقعی هنوز شواهد ندارند.
- backup: هیچ DB واقعی migrate نشد؛ مسیر، checksum و restore test در این برش `N/A` است و قبل از اجرای clone MySQL اجباری می‌ماند.
- ردیف‌ها در legacy test: `admins 2 -> 2`، `admin_roles 0 -> 3`، `admin_hierarchy_settings 0 -> 1`، `system_owner 0 -> 0`، `admin_hierarchy 0 -> 2`.
- backfill: فقط self-rowهای قطعی closure ساخته شد؛ Owner، Parent و User backfill همگی صفر. reason codeها تا اجرای `set-owner` تولید نمی‌شوند.
- حفظ داده: Admin IDهای `10` و `20`، username و `is_sudo` حفظ شدند؛ `role_id` و `parent_admin_id` برابر `NULL` و feature flag خاموش ماند. جدول‌های credit/usage/User لمس نشدند.
- rollback application: تغییرات فقط افزایشی‌اند؛ image قبلی ستون‌ها و جدول‌های جدید را نادیده می‌گیرد. downgrade schema و rollout production در این برش اجرا نشد.
- indexها: subtree از PK `(ancestor_id, descendant_id)`، ancestor lookup از `(descendant_id, ancestor_id, depth)` و direct-child lookup از `(parent_admin_id, id)` استفاده می‌کند؛ index اضافه نقش تا مشاهده query واقعی ساخته نشد.

وضعیت Git هنگام ایجاد سند:

```text
branch: agent/heisenberg-v4.8.0
HEAD: fd73e03
tag: v4.8.0
```

فرمان‌های شروع مجدد پس از قطع برق:

```powershell
Get-Content -Raw AGENTS.md
Get-Content -Raw docs/ADMIN_HIERARCHY_ROADMAP_FA.md
git status --short --branch
git remote -v
git ls-remote --tags origin
git log -3 --oneline --decorate
```

## لاگ پیشرفت

| زمان | مرحله | وضعیت | تغییرات و شواهد | commit | آزمون | قدم بعدی |
|---|---:|---|---|---|---|---|
| `2026-08-18` | ۰ | کامل | بررسی Graphify، مدل‌های `Admin` و `User`، scope فعلی، CLI sudo و سیاست اعتبار؛ ایجاد این سند | `—` | فقط تحلیل و بررسی read-only | نهایی‌کردن تصمیم‌های مرحله ۱ با کاربر |
| `2026-08-18` | ۱ | در حال طراحی | ثبت نقش‌های Owner/Super Admin/Admin، API خارجی Owner-only، محدودیت Node/Core/Xray/reset کل، داشبورد حساب غیر Owner و مدیریت User در subtree | `—` | `git diff --check` پس از ویرایش سند؛ بدون تست اجرایی | دریافت و ثبت باگ‌های کاربر؛ ادامه فقط در `PLAN_ONLY` |
| `2026-08-18` | ۱ | در حال طراحی | ثبت مجوز و سهمیه تمدید، created-traffic برای Admin، قطع خودکار، غیرفعال‌سازی گروهی، Planهای سلسله‌مراتبی، فرم PLAN_ONLY و باگ‌های `BUG-ADM-001`/`BUG-USR-002` | `—` | تحلیل Graphify و بررسی read-only مسیرهای policy/template/disable؛ بدون تست اجرایی | بازبینی کاربر و دریافت reproduction باگ‌ها؛ ادامه فقط در `PLAN_ONLY` |
| `2026-08-18` | ۱ | در حال طراحی | ثبت قانون دائمی شروع جلسه و سازگاری update؛ baseline تأییدشده `v4.8.0@fd73e03`؛ طراحی compatibility mode و backfill Parent/Owner با reason code | `—` | Git tag/GitHub Release و مسیرهای migration/rollback به‌صورت read-only بررسی شد | بازبینی کاربر؛ پیش از هر تغییر release baseline دوباره تأیید شود |
| `2026-08-18` | ۱ | در حال طراحی | تکمیل `BUG-ADM-001` به‌عنوان خرابی `concurrent_user_limit`، ثبت blocker بحرانی `BUG-DVL-003` برای نبود IP/log و اتصال آن به `BUG-USR-002` | `—` | بررسی read-only مدل‌ها، DeviceLimitEngine، API و UI؛ بدون تست اجرایی | رفع به ترتیب IP collector، device limit، سپس disable sync؛ فقط بعد از خروج از `PLAN_ONLY` |
| `2026-08-18` | ۱ | کامل | دستور شروع کاربر ثبت شد؛ تصمیم‌های نقش، reparent، env، عمق، API خارجی، suspension، Plan و تمدید قفل شدند؛ baseline remote/GitHub/GHCR بازتأیید شد | `—` | remote tag peeled به `fd73e03`؛ Latest Release=`v4.8.0`؛ GHCR digest=`sha256:374b0e18d4daa289d99692256f3fb264ddd93eca9a1f752837d6d7a17e1ed9b8` | طراحی و تست migration افزایشی foundation |
| `2026-08-18` | ۲/۳ | در حال اجرا | افزودن مدل و migration `e2a6c1f4b903`: role lookup، Parent nullable، external API flag، settings singleton خاموش، Owner singleton خالی و closure self-row؛ فایل‌ها: `app/db/models.py`، migration جدید، `tests/test_admin_hierarchy_migration.py`، `tests/test_marzhelp_migration_backup.py` | `—` working tree | `2 passed` migration legacy/partial-rerun؛ `1 passed` full Alembic chain؛ `9 passed` Admin regression؛ MySQL test=`skipped` چون `MYSQL_TEST_URL` موجود نیست؛ `compileall` و `git diff --check` موفق؛ Graphify تا HEAD `fd73e03` به‌روزرسانی شد؛ `alembic heads` محلی به‌علت نبود Xray binary شکست خورد و بررسی AST head=`e2a6c1f4b903` را تأیید کرد | اجرای migration روی clone واقعی MySQL 8.0 و ثبت backup/restore/partial-DDL/rollback evidence |
| `2026-08-19` | ۲ تا ۶ | در حال اجرا | توسعه migration با ledger/token/suspension/bulk/Plan؛ پیاده‌سازی closure scope، `set-owner`، انتقال اعتبار idempotent، توکن hash‌شده، تعلیق قابل‌بازگشت، bulk job cursor-resume، Plan immutable، renewal atomic، قطع خودکار، scope کاربران/audit/device/system و UI responsive hierarchy/Plan/account | `—` working tree | `23 passed` برای hierarchy service، migration، full chain و Admin regression؛ `compileall` موفق؛ TypeScript و گیت MySQL در حال تکمیل | رفع هر خطای build، اجرای کل suite و گیت MySQL 8.0؛ سپس Graphify و release |
| `2026-08-19` | ۳ تا ۱۳ | پیاده‌سازی محلی کامل؛ گیت خارجی باز | تکمیل hierarchy/API/CLI/UI، تمدید مستقل با Plan، audit عملیات حساس، بستن conflict کلید idempotency، اصلاح جهت reclaim ledger، حذف دو index تکراری و حذف N+1 در tree؛ Graphify=`4796 nodes/10304 edges` | `14d9592` | `82 passed, 2 skipped`؛ skipها فقط MySQL؛ TypeScript=`0`، Vite production build=`0`، `compileall`=`0`، `bash -n`=`0`، YAML parse=`OK` | احراز هویت GitHub؛ push branch/tag `v4.9.0`؛ انتظار برای workflow MySQL/backup/rollback و انتشار |
| `2026-08-19` | ۱۴ | شکست گیت MySQL؛ اصلاح محلی کامل | branch و tag `v4.9.0` push شدند؛ workflow `32195714228` در job `95899175897` با MySQL error `3818` شکست خورد، چون `SMALLINT` primary key جدول singleton به‌طور ضمنی `AUTO_INCREMENT` شده بود؛ build/release skip شد. برای `v4.9.1` شناسه شش جدول مرجع ثابت و singleton صریحاً `autoincrement=False` شد | `dc357cc` + working tree | `83 passed, 2 skipped`؛ تست DDL جدید هر شش جدول؛ compileall/YAML/diff-check سبز؛ Graphify=`4796/10304/442` | commit و tag `v4.9.1`؛ دنبال‌کردن workflow و release تا نتیجه نهایی |
| `2026-08-19` | ۱۴ | شکست دوم گیت MySQL؛ اصلاح کوچک در حال آزمون | `v4.9.1@cb696c4` خطای قبلی را رفع کرد، ولی run `32196467586` در job `95901398510` با MySQL error `1170` روی unique index فیلد `token_hash BLOB` شکست خورد. نوع hash ثابت SHA-256 برای `v4.9.2` به `BINARY(32)` تغییر کرد | `cb696c4` + working tree | backend regression سبز؛ migration واقعی در run دوم خطا داد | تست regression؛ commit/tag `v4.9.2`؛ یک retry نهایی workflow |
| `2026-08-19` | ۱۵ | کامل و منتشرشده | `v4.9.2` منتشر شد؛ MySQL 8.0 fresh/legacy/partial-DDL، backup/checksum/restore، rollback application `v4.8.0`، frontend build و image چندمعماری همگی موفق؛ Latest Release و GHCR `v4.9.2/latest` ساخته شدند | `ded182ec2f50b3fe553752947eff27be7912c83e` | Actions run `32196890824`=`success`؛ digest=`sha256:c0fdbfb7c4af7b2360ca8718c83f20ccf4dca7534fa38becb550e81bd6096973` | backup دیتابیس واقعی و rollout کنترل‌شده `v4.9.2` |
| `2026-08-19` | ۱۶ | پیاده‌سازی کامل؛ آماده انتشار | root cause تغییر `mysql:latest` از 8.x به `26.7.0` مشخص شد؛ نصب تازه latest، دستور امن `marzban mysql-upgrade`، logical/physical backup با checksum، مسیر `8.0 → 8.4 → 9.7 → latest`، health gate هر مرحله و اصلاح restore مبتنی بر GTID اضافه شد | `8ac5a23` + `150e9d6` | Actions run `32199333844`: MySQL 8.0=`success`، MySQL latest=`success`، existing-volume upgrade=`success`؛ تست محلی هدفمند `4 passed` | bump/tag/release immutable `v4.9.3` و ثبت digest نهایی GHCR |
| `2026-08-20` | Stage 1 repair | کد و آزمون محلی کامل؛ گیت خارجی باز | PRE-STAGE: root/worktree/remote/toolchain و Graphify بررسی شد؛ Graphify به `3258 nodes/7981 edges/383 communities` و freshness=`0` رسید. فایل‌های Stage 1: `app/db/crud.py`، `app/routers/user.py`، `cli/user.py`، `app/dashboard/src/{hooks/useGetUser.tsx,utils/authStorage.ts,contexts/DashboardContext.tsx,pages/Login.tsx,components/Header.tsx}`، `tests/test_user_access_scope.py` و این roadmap. تغییرات قبلی کاربر در Xray/status دست‌نخورده ماند | `e28312f` + working tree | pre-fix=`3 failed, 5 passed`؛ targeted=`32 passed`؛ full=`100 passed, 2 skipped, 464 warnings`؛ تست authorization افزوده‌شده=`1 passed`؛ TypeScript=`0`، Vite production build=`0`؛ MySQL/Xray/browser زنده اجرا نشد | Graphify update/diagnose و diff review؛ گزارش و توقف Stage 1؛ سپس انتظار برای دستور صریح Stage 2 |
| `2026-08-21` | Stage 2 repair | کد و آزمون محلی کامل؛ گیت Xray/MySQL زنده باز | `MRZ-STATE-003`: جلوگیری از resurrect شدن User غیرفعال در reset تکی و release پنالتی Device Limit؛ حفظ `on_hold` در reset؛ اصلاح ترتیب بررسی `active-next`؛ افزودن ماتریس وضعیت و contract عملیات Xray | `e28312f` + working tree | pre-fix=`3 failed, 7 passed`؛ اثبات عبارت upstream برای disabled=`1 failed`؛ Stage 2=`11 passed`؛ targeted=`66 passed`؛ full=`112 passed, 2 skipped, 531 warnings` | Graphify update/diagnose و diff review؛ گزارش و توقف Stage 2؛ سپس انتظار برای دستور صریح Stage 3 |
| `2026-08-21` | Stage 3 repair | کد و آزمون محلی کامل؛ آماده انتشار `v4.9.8` | `MRZ-DL-004`: پشتیبانی امن parser از sourceهای مستقیم، `tcp:IPv4`، IPv6 و `tcp:[IPv6]` در Xray `26.7.28`؛ جلوگیری از fallback به destination؛ diagnostics محدود و sudo-only؛ اثبات threshold و handoff grace | `e28312f` + working tree | pre-fix=`1 failed, 1 passed`؛ Stage 3=`21 passed`؛ targeted=`71 passed`؛ full=`117 passed, 2 skipped, 533 warnings`؛ TypeScript/Vite production build=`0`؛ `v4.9.7` CI فقط با contract قدیمی نسخه شکست خورد | Graphify update/diff review؛ commit/tag/release `v4.9.8`؛ توقف و انتظار برای دستور صریح Stage 4 |
| `2026-08-22` | Runbook V3 Stage 1 | `PASS`؛ فقط `BUG-04/09/10` | intent داخلی `edit/renew`، quota صریح برای Telegram charge و Next Plan، transaction مشترک reset+renew، حفظ capture حذف Device Limit و تشخیص Owner واقعی | `b45e3af` + working tree | pre-fix=`3 failed, 1 passed`؛ Stage 1=`5 passed`؛ adjacent=`78 passed`؛ compileall/diff-check/Graphify=`PASS`؛ MySQL/Telegram زنده=`NOT EXECUTED` | توقف؛ انتظار برای دستور صریح Stage 2؛ بدون commit/push/tag/release |
| `2026-08-22` | Runbook V3 Stage 2 | `PASS`؛ فقط `BUG-05/06` و `R-RES-01..03` | Ledger توسعه‌یافته با target/resource/delta/before-after؛ Grant/Reclaim و audit اتمیک؛ CAS همزمانی؛ initial credit والد-محور؛ Renewal API/UI مجاز؛ migration=`7d2c6a4e9b10` | `b45e3af` + working tree | pre-fix concurrency=`1 failed, 6 passed`؛ final targeted+adjacent=`90 passed` روی SQLite و MySQL/InnoDB `8.0.43`؛ UI auth/TypeScript/Vite/compileall/diff-check/Graphify=`PASS` | توقف؛ انتظار برای دستور صریح Stage 3 و حل `D-05/D-09`؛ بدون commit/push/tag/release |
| `2026-08-22` | Runbook V3 Stage 3 | `BLOCKED` پیش از implementation | Stage 0 read-only و Graphify مسیر mode/ledger/usage/migration را بررسی کرد؛ مدل legacy برای قرارداد تجاری جدید evidence کافی نیست؛ `D-05` و `D-09` حل نشده‌اند | `b45e3af` + working tree | source/schema tests=`NOT EXECUTED`؛ Git/remote/GitHub/GHCR preflight=`PASS`؛ source/schema changes=`0` | دریافت تصمیم صریح Owner برای refund/reclaim، unlimited-device Seat cost و legacy migration/default؛ سپس تکرار Stage 0؛ بدون commit/push/tag/release |
| `2026-08-22` | Runbook V3 Stage 4 | `BLOCKED` پیش از implementation | prerequisite برابر `Stage 3 PASS` برقرار نیست و `D-10` نیز حل نشده است؛ Graphify مسیرهای Plan/Inbound/Host/access/subscription را فقط read-only بررسی کرد | `b45e3af` + working tree | source/UI/schema tests=`NOT EXECUTED`؛ Git/remote/GitHub/GHCR preflight=`PASS`؛ source/UI/schema changes=`0` | ابتدا Stage 3 را پس از تصمیم‌های Owner به `PASS` برسان؛ سپس `D-10` را تعیین و Stage 4 را تکرار کن؛ بدون commit/push/tag/release |
| `2026-08-22` | Runbook V3 تصمیم `D-05` | `RESOLVED`؛ implementation هنوز `NOT EXECUTED` | no auto-refund؛ Refund Request پایدار با snapshot immutable؛ وضعیت‌های `PENDING/APPROVED/REJECTED/CANCELLED`؛ approval-only ledger credit؛ authorization/idempotency/transaction/concurrency/audit الزامی | `b45e3af` + working tree | docs contract و `git diff --check`؛ source/schema tests=`NOT EXECUTED` | دریافت `D-09` و legacy migration/default؛ سپس اجرای واقعی Stage 3؛ بدون commit/push/tag/release |
| `2026-08-22` | Runbook V3 Stage 3 resume | `IN PROGRESS`؛ فقط Stage 3 | `D-09` resolved: Seat cost برابر device/concurrency مثبت و محدود؛ fallback ممنوع. Legacy resolved: `LEGACY_COMPAT` تا assignment صریح Owner و بدون balance reinterpretation | `b45e3af` + working tree | Stage 0 Git/tag/GHCR/Graphify=`PASS`؛ GitHub REST=`403 Forbidden` با same-session verification؛ implementation tests هنوز `NOT EXECUTED` | migration/service/API/tests Stage 3؛ MySQL evidence؛ توقف بدون Stage 4/انتشار |
| `2026-08-22` | Runbook V3 Stage 3 final | `PASS`؛ فقط Stage 3 | strategy صریح چهار mode؛ migration `8c4d7e9f2a31` با backfill صرفاً `LEGACY_COMPAT`؛ Seat بدون fallback و بدون auto-return؛ Used delta-derived؛ Allocated charge بدون auto-refund؛ Refund Request پایدار با snapshot/history/auth/idempotency/row-lock و approval-only ledger | `b45e3af` + working tree | targeted=`54 passed, 1 skipped`؛ MySQL/InnoDB `8.0.43` migration+concurrency=`2 passed`؛ full=`150 passed, 3 skipped`؛ compileall/diff-check/Graphify=`PASS` (`3869/9331/441`) | توقف؛ حل `D-10` و دستور صریح پیش از Stage 4؛ بدون commit/push/tag/release/publish |
| `2026-08-22` | Runbook V3 Stage 4 start | `BLOCKED` پیش از implementation | Stage 3=`PASS`؛ Graphify و source نشان دادند empty Inbound مجاز، proxy خالی محتمل و `PlanHost` غایب است؛ D-10 تعیین نمی‌کند empty باید reject، snapshot-default یا dynamic-inherit باشد | `b45e3af` + working tree | Stage 0 root/HEAD/upstream/tag/GHCR/diff-check=`PASS`؛ GitHub Latest API=`403 Forbidden`؛ source/schema/UI tests=`NOT EXECUTED` | دریافت تصمیم صریح D-10؛ سپس تکرار Stage 0 و اجرای Stage 4؛ بدون commit/push/tag/release/publish |
| `2026-08-22` | Runbook V3 Stage 5 start | `BLOCKED` پیش از implementation | prerequisite سخت برقرار نیست: Stage 4=`BLOCKED` روی `D-10` و Gate A=`NOT EXECUTED`؛ تصمیم‌های `D-01` و `D-03` نیز بازند؛ Graphify مسیرهای Plan create/renew، raw create، billing و namespace را read-only بررسی کرد | `b45e3af` + working tree | Stage 0 root/HEAD/upstream/tag/GitHub Latest/GHCR/diff-check=`PASS`؛ source/schema/UI/targeted tests=`NOT EXECUTED`؛ source diff fingerprint=`87553abc0fa609214c1b1b9c72cef4541d6d89db` | تعیین D-10، تکمیل Stage 4 و Gate A؛ سپس تعیین D-01/D-03 و شروع مجدد Stage 5؛ حفظ D-05؛ بدون commit/push/tag/release/publish |
| `2026-08-22` | Runbook V3 D-10 / Stage 4 resume | `IN PROGRESS`؛ فقط Stage 4 | `D-10 = Option 1` تأیید شد: Plan بدون Inbound یا Host لازم رد؛ disabled/deleted/unavailable/out-of-scope fail-closed؛ validation/create/subscription همسان؛ بدون snapshot default/dynamic inheritance | `b45e3af` + working tree | Stage 0 remote tag/GitHub Latest/GHCR/diff-check=`PASS`؛ Graphify impact analysis در حال اجرا | schema/backend/UI سپس targeted/adjacent/MySQL و Gate A؛ توقف پیش از Stage 5؛ بدون commit/push/tag/release/publish |
| `2026-08-22` | Runbook V3 Stage 4 final | `PASS`؛ فقط Stage 4 | scope صریح versioned برای Inbound/Host؛ empty/disabled/deleted/unavailable/mismatch/out-of-scope همگی fail-closed؛ validation و create/renew/subscription همسان؛ UI انتخاب nested؛ migration=`9f6a2c8d4e10`؛ legacy Plan بدون Host inferred نمی‌شود | `b45e3af` + working tree | targeted=`17 passed`؛ Gate A=`124 passed`؛ full=`160 passed`؛ MySQL/InnoDB `8.0.43` migration=`1 passed`؛ UI utility/TypeScript/Vite/compileall/diff-check/Graphify=`PASS` (`3916/9517/446`)؛ browser/live infrastructure=`NOT EXECUTED` | توقف کامل؛ Stage 5 شروع نشود؛ ابتدا تصمیم صریح `D-01/D-03` و دستور جدید؛ بدون commit/push/tag/release/publish/deploy |
| `2026-08-22` | Runbook V3 D-01/D-03 / Stage 5 resume | `IN PROGRESS`؛ فقط Stage 5 | D-01: تمدید Seat مانند creation و به‌اندازه device count Plan شارژ اتمیک/idempotent؛ expiry بدون بازگشت. D-03: prefix پایدار و یکتای هر creator برای همه Userهای مشتری جدید از Owner تا Sub-admin؛ login ادمین و User موجود بدون rename | `b45e3af` + working tree | Stage 4=`PASS`؛ Gate A=`124 passed`؛ Stage 0 root/HEAD/upstream/diff-check/Graphify=`PASS`؛ source tests هنوز `NOT EXECUTED` | migration و backend/UI Stage 5؛ targeted/concurrency/MySQL/regression؛ Graphify/docs؛ توقف پیش از Stage 6 و بدون publication |
| `2026-08-23` | Runbook V3 Stage 5 final | `PASS`؛ فقط Stage 5 | migration=`3a7e5c1b8d42`؛ prefix پایدار و unique برای همه creatorها؛ raw Seat fail-closed؛ Used/Allocated simple create با network/device server-derived؛ Seat Plan renewal اتمیک و idempotent بدون بازگشت اعتبار در expiry/delete | `b45e3af` + working tree | targeted=`18 passed`؛ adjacent=`101 passed, 1 skipped`؛ full=`167 passed, 3 skipped`؛ MySQL/InnoDB `8.0.43`=`1 passed`؛ TypeScript/Vite/UI utility/compileall/diff-check=`PASS`؛ Graphify export=`BLOCKED/UNCERTAINTY` با حفظ graph قبلی؛ browser/live=`NOT EXECUTED` | توقف کامل پیش از Stage 6؛ full Graphify rebuild بعداً؛ بدون commit/push/tag/release/publish/deploy |
| `2026-08-23` | Runbook V3 Stage 6 start | `IN PROGRESS`؛ فقط Stage 6 | Stage 0 read-only تکرار شد؛ Stage 5=`PASS`؛ Trial نامحدود از همان حسابداری mode عبور می‌کند: Seat با device محدود، Used با مصرف واقعی و Allocated محدود به‌صورت fail-closed | `b45e3af` + working tree | root/HEAD/upstream/status/diff-check/Graphify query=`PASS`؛ remote tag refresh=`UNCERTAINTY` به‌علت TLS؛ source/schema/UI tests هنوز `NOT EXECUTED` | schema/backend/UI/migration و targeted/adjacent/MySQL؛ سپس Graphify/docs؛ توقف پیش از Stage 7 و بدون publication |
| `2026-08-23` | Runbook V3 Stage 6 final | `PASS`؛ فقط Stage 6 | Trial Plan/assignment صریح و immutable؛ quota مستقل Admin با Owner grant/reclaim ledger؛ مصرف اتمیک/idempotent؛ cleanup مبتنی بر metadata با preview، scope، audit و حفظ deleted-user accounting؛ migration=`5b8d1f3a7c64` | `b45e3af` + working tree | targeted=`9 passed`؛ adjacent=`83 passed, 1 skipped`؛ full=`176 passed, 4 skipped`؛ MySQL/InnoDB `8.0.43` migration+last-quota race+same-key idempotency=`1 passed`؛ TypeScript/Vite/UI utility/compileall/diff-check=`PASS`؛ Graphify=`3988/9884/436`؛ browser/live=`NOT EXECUTED` | توقف کامل پیش از Stage 7؛ TLS remote و 11 zero-node Graphify file=`UNCERTAINTY` غیرمسدودکننده؛ بدون commit/push/tag/release/publish/deploy |
| `2026-08-23` | بهینه‌سازی دامنه Stage 7–13 | `PASS`؛ فقط governance docs | حذف الزام future برای production legacy فرضی و cross-DB؛ baselineهای معتبر=`v4.9.8` و schema فعلی؛ DB production=`MySQL 8.x / InnoDB`؛ SQLite فقط unit harness؛ PostgreSQL/TimescaleDB پروژه آینده؛ `LEGACY_COMPAT` موجود بدون توسعه یا cleanup | `b45e3af` + working tree | فقط Runbook/Roadmap تغییر کرد؛ application/schema/migration/tests=`UNCHANGED`؛ scope/precedence و `git diff --check` بررسی شد | توقف؛ Stage 7 شروع نشده؛ در دستور بعد Stage 0 و تصمیم‌های `D-02/D-04`؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-23` | Runbook V3 Stage 7 start | `BLOCKED` پیش از implementation | prerequisiteهای Stage 2/3/5=`PASS`؛ `D-02` واحد settlement ارجاع و `D-04` scope freeze هنوز unresolved؛ حدس ممنوع | `b45e3af` + working tree | Stage 0 root/HEAD/upstream/remote tag/diff-check/Graphify query=`PASS`؛ source/schema/migration/UI/tests/MySQL=`NOT EXECUTED` | دریافت تصمیم صریح `D-02` و `D-04`؛ تکرار Stage 0؛ ادامه فقط Stage 7؛ Stage 8 و publication ممنوع |
| `2026-08-23` | Runbook V3 Stage 8 start | `BLOCKED` پیش از implementation | Stage 7=`BLOCKED` و prerequisite `Stage 7 PASS` برقرار نیست؛ `D-06` target semantics و `D-07` batch transaction/partial failure/retry نیز unresolved | `b45e3af` + working tree | root/HEAD/upstream/remote tag/diff-check/Graphify query=`PASS`؛ source/schema/query/UI/tests/MySQL=`NOT EXECUTED` | ابتدا حل `D-02/D-04` و تکمیل Stage 7؛ سپس تصمیم `D-06/D-07` و resume فقط Stage 8؛ Stage 9/publication ممنوع |
| `2026-08-23` | Runbook V3 D-02/D-04 / Stage 7 resume | `IN PROGRESS`؛ فقط Stage 7 | D-02 attribution/audit-only بدون automatic reward؛ D-04 Owner Freeze روی target+تمام descendant Admin/User با restoration provenance-safe، audit و idempotency | `b45e3af` + working tree | Stage 0 root/HEAD/upstream/remote tag/diff-check/Graphify query=`PASS`؛ prerequisites Stage 2/3/5=`PASS` | schema/backend/UI Stage 7؛ targeted/adjacent/MySQL؛ Graphify/docs؛ توقف پیش از Stage 8 و بدون publication |
| `2026-08-23` | Runbook V3 Stage 7 final | `PASS`؛ فقط Stage 7 | referral attribution جدا از hierarchy و بدون reward؛ Owner-only config؛ full-subtree Owner Freeze با snapshot دقیق Admin/User، provenance-safe unfreeze، session blocking، audit، idempotency و MySQL deadlock retry؛ migration=`7c9a2e4f1b65` | `b45e3af` + working tree | targeted=`16 passed`؛ adjacent=`72 passed, 2 skipped`؛ MySQL/InnoDB `8.0.43` fresh/current-schema migration + freeze/referral concurrency=`1 passed` و downgrade/re-upgrade=`PASS`؛ TypeScript/Vite=`1749 modules`؛ UI auth=`PASS`؛ Graphify=`4031/10110/446`؛ compileall/diff-check=`PASS` | توقف کامل پیش از Stage 8؛ browser/live infra و full suite=`NOT EXECUTED`؛ 11 zero-node Graphify file و 6 `.test-*` inaccessible=`UNCERTAINTY` غیرمسدودکننده؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-23` | Runbook V3 Stage 8 resume | `BLOCKED` پیش از implementation | prerequisiteهای Stage 2/3/6/7=`PASS`؛ `D-06` target/default/filter semantics و `D-07` atomicity/partial-failure/resume/retry هنوز unresolved و حدس ممنوع | `b45e3af` + working tree | root/HEAD/upstream/diff-check/Graphify query=`PASS`؛ source/schema/query/UI/targeted/adjacent/MySQL=`NOT EXECUTED` | دریافت تصمیم صریح `D-06/D-07`؛ تکرار preflight و resume فقط Stage 8؛ Stage 9 و commit/push/tag/release/deploy/publish ممنوع |
| `2026-08-23` | Runbook V3 Stage 8 final | `PASS`؛ فقط Stage 8 | scope صریح سه‌حالته و authorization server-side؛ snapshot immutable؛ job دائمی با target status/error/fingerprint؛ chunk محدود و transaction مستقل هر target؛ retry فقط incomplete/retryable؛ Bulk User و Admin Grant/Reclaim؛ UI preview/count/report؛ migration=`2e8c4a6f9b17` | `b45e3af` + working tree | targeted=`33 passed`؛ adjacent=`81 passed, 2 skipped`؛ MySQL/InnoDB `8.0.43` migration rerun+rollback، دو worker/۲۰ User، exact-once ledger و `EXPLAIN`=`1 passed`؛ TypeScript/Vite=`1749 modules`؛ UI auth/compileall/diff-check=`PASS`؛ Graphify=`4146/10577/452` | توقف کامل؛ Stage 9 شروع نشده؛ full suite/browser/Core/Node/Tunnel=`NOT EXECUTED`؛ 11 zero-node Graphify file=`UNCERTAINTY` غیرمسدودکننده؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-23` | Runbook V3 Stage 9 final + Gate B | `PASS`؛ فقط Stage 9 و Gate B | phone اجباری Admin جدید بدون backfill فرضی؛ UI mode-aware بدون Discord؛ Seat Grant/Reclaim صحیح؛ dashboard scope-aware با week/timezone و چهار mode؛ migration=`6d4f2a9c8e10` و rollback FK-safe | `b45e3af` + working tree | targeted=`14 passed`؛ Gate B=`93 passed, 2 skipped`؛ MySQL/InnoDB `8.0.43` Stage 9=`1 passed` و hierarchy/bulk=`2 passed`؛ ۲۰۰۰ User + `EXPLAIN` دو index؛ TypeScript/Vite=`1750 modules`؛ compileall/diff-check=`PASS`؛ Graphify=`4195/10733/452` | توقف کامل پیش از Stage 10؛ full suite/browser/Core/Node/Tunnel=`NOT EXECUTED`؛ 11 zero-node Graphify file، دو skip اختیاری و 6 `.test-*` inaccessible=`UNCERTAINTY` غیرمسدودکننده؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-23` | Runbook V3 Stage 10 final | `PASS`؛ فقط Stage 10 | business error code و fallback امن فارسی؛ Unlimited؛ pagination واقعی `10/25/50` با رد صریح مقدار/offset نامعتبر؛ search/filter/sort server-side، metadata صفحه و tie-breaker یکتا؛ migration=`1a9e7c3d5b20` با دو index مرکب | `b45e3af` + working tree | targeted=`32 passed`؛ adjacent=`48 passed`؛ MySQL/InnoDB `8.0.43` migration upgrade/downgrade، `SHOW INDEX`، ۱۰٬۰۰۰ User، `EXPLAIN ANALYZE` و deep-offset timing=`1 passed`؛ TypeScript/Vite=`1751 modules`؛ Graphify=`4217/10795/455` | توقف کامل پیش از Stage 11؛ full suite/browser/Core/Node/Tunnel=`NOT EXECUTED`؛ bundle-size warning، 11 zero-node Graphify file و 6 `.test-*` inaccessible=`UNCERTAINTY` غیرمسدودکننده؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-23` | Runbook V3 Stage 11 start | `BLOCKED` پیش از implementation | Stage 10=`PASS`؛ `D-08` Backup policy و `D-11` outbox/audit retention/archive/purge هنوز unresolved؛ حدس درباره retention/security/operations ممنوع | `b45e3af` + working tree | root/HEAD/upstream/tag/remote/status=`PASS`؛ Graphify query=`PASS`؛ source/schema/migration/targeted/adjacent/MySQL/failure-path/retry/restore/live Telegram=`NOT EXECUTED` | دریافت تصمیم صریح `D-08/D-11`؛ سپس تکرار preflight و resume فقط Stage 11؛ Stage 12 و commit/push/tag/release/deploy/publish ممنوع |
| `2026-08-23` | Runbook V3 Stage 11 final | `PASS`؛ فقط Stage 11 | D-08/D-11 resolved؛ outbox/audit transactional و idempotent؛ retry/dead-letter؛ retention 30/90 روز و audit دائمی؛ backup MySQL سی‌دقیقه‌ای AES-256-GCM/SHA-256، spool و state مجزای generation/delivery؛ migration=`4c8e1a7d9b30` | `b45e3af` + working tree | targeted=`5 passed`؛ adjacent شامل targeted=`73 passed`؛ MySQL/InnoDB `8.0.43` migration/rollback، index/EXPLAIN، concurrency exact-once 40 event و restore disposable=`1 passed`؛ compile/diff-check=`PASS`؛ Graphify=`4256/10915/467` | توقف پیش از Stage 12؛ live Telegram و production restore=`NOT EXECUTED`؛ `mysqldump` deployment=`UNCERTAINTY`؛ Bot API رسمی 50 MB و default برنامه 45 MiB؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-23` | Runbook V3 Stage 12 start | `BLOCKED` پیش از external action | Stage 11=`PASS`؛ Runbook نیازمند explicit Owner authorization و authenticated GitHub است؛ ممنوعیت جاری push/publish با ساخت fork تعارض دارد؛ حساب مقصد تعیین نشده | `b45e3af` + working tree | upstream `gozargah/Marzban-scripts` reachable، HEAD=`24a772d297c7518dae7650b8f106419e73813cda`؛ `gh auth status`=`not logged in`؛ source/installer/targeted/adjacent/DB=`NOT EXECUTED` | دریافت destination account/org، GitHub login و مجوز محدود fork/push؛ سپس تکرار preflight و resume فقط Stage 12؛ Stage 13/tag/release/deploy ممنوع |
| `2026-08-23` | Runbook V3 Stage 12 authorized resume | `BLOCKED` پیش از fork | Owner مقصد و مجوز محدود fork/commit/push فقط برای `smorad3363/Marzban-scripts` را تأیید کرد؛ authentication همچنان برقرار نیست | `b45e3af` + working tree | `gh auth status`=`not logged in`؛ `GH_TOKEN_PRESENT=false`؛ `GITHUB_TOKEN_PRESENT=false`؛ fork مقصد=`Repository not found`؛ upstream HEAD=`24a772d297c7518dae7650b8f106419e73813cda` | login امن GitHub به `smorad3363`؛ تکرار Stage 12؛ Gate مانع شروع Stage 13؛ main Marzban و release actions ممنوع |
| `2026-08-23` | Runbook V3 Stage 12 final | `PASS`؛ فقط Stage 12 | fork معتبر `smorad3363/Marzban-scripts` با parent اصلی و upstream sync؛ self-update به fork؛ Owner URL با commit ثابت pin شد | `b45e3af` + working tree؛ fork=`1ef7ad62d2c16e4450f1a0de9678c8a8c883b154` | upstream=`24a772d...`؛ ahead/behind=`1/0`؛ raw/commit blob=`c7c1270...`؛ دو `bash -n`=`PASS`؛ release contract=`1 passed`؛ compile/diff-check=`PASS` | Stage 13 مجاز شد؛ نصب واقعی Node=`NOT EXECUTED` چون target لینوکسی disposable موجود نیست؛ main Marzban بدون publication |
| `2026-08-23` | Runbook V3 Stage 13 final gate | `PASS` برای gate محلی/disposable؛ `READY FOR NEXT ENVIRONMENT` | بدون feature جدید؛ SQLite migration خارج production evidence؛ دو اصلاح فقط test-harness؛ نسخه عمداً `4.9.8` ماند | `b45e3af` + working tree؛ upstream=`0/0`؛ staged/stash=`0/0` | backend=`212 passed, 9 skipped`؛ frontend utility/auth/build=`PASS` و `1751 modules`؛ شش MySQL/InnoDB `8.0.43` test=`PASS`؛ head=`4c8e1a7d9b30`؛ Graphify=`4260/10919/461`؛ compile/release-contract/diff-check=`PASS` | Browser/Core/Node/Tunnel/live Telegram/native mysqldump=`NOT EXECUTED`؛ Graphify 11 zero-node و bundle warning=`UNCERTAINTY`؛ production migration/restore و main publish انجام نشد؛ bump/release `v5.0.0` نیازمند مجوز جدا |
| `2026-08-23` | آماده‌سازی انتشار `v5.0.0-rc.1` | `PASS` برای pre-publication gate؛ فقط release candidate | مجوز صریح برای commit/push/tag/prerelease مخزن `smorad3363/Marzban`؛ نسخه runtime و قرارداد release به RC تغییر کرد؛ historical referenceها حفظ شدند؛ prerelease نباید `latest` را جابه‌جا کند | `b45e3af` + working tree | origin/مالک/branch/Stage 1–13 و چهار حذف tracked بررسی شد؛ دو حذف asset عمدی؛ دو حذف doc نامطمئن خارج commit؛ secret scan بدون credential واقعی؛ `git diff --check`=`PASS`؛ release contract=`1 passed`؛ workflow YAML=`PASS` | manifest دقیق commit شود؛ سپس branch/tag/prerelease منتشر شود؛ بدون deploy و بدون final `v5.0.0` |
| `2026-08-23` | آماده‌سازی `v5.0.0-rc.2` | `PASS` برای pre-publication gate؛ فقط CI orchestration | `rc.1` immutable و منتشرشده در `df23dd8` حفظ شد؛ چهار تست MySQL Stage 8–11 از suite مشترک جدا و روی MySQL 8.0 با DB مستقل اجرا می‌شوند؛ application behavior جز version بدون تغییر | `df23dd8` + working tree | failure run=`32609917367`؛ remote tag/release `rc.1` بازتأیید شد؛ regression عمومی اصلاح‌شده=`212 passed, 3 skipped`؛ local MySQL/Docker=`NOT EXECUTED` چون runtime/port موجود نبود | YAML/diff/secret/release-contract gate؛ سپس commit/push/tag/prerelease و انتظار کامل CI/MySQL/image evidence؛ بدون deploy/final v5 |
| `2026-08-23` | بازطراحی UX/UI ادمین | implementation=`PASS`؛ browser gate=`BLOCKED` | فرم یک‌مرحله‌ای حذف و Drawer پنج‌مرحله‌ای با `100dvh`، body scroll مستقل، footer ثابت و Advanced بسته جایگزین شد؛ Grant/Reclaim گروهی و عملیات هر ادمین progressive disclosure شدند؛ جدول به پنج ستون اصلی و جزئیات expandable کاهش یافت؛ Dashboard به account/KPI/trends/breakdown/system/quick-actions گروه‌بندی شد؛ backend/schema تغییر نکرد | `49c9e1d` + working tree | TypeScript+Vite=`PASS`, `1752 modules`؛ Admin UX contract=`22 assertions passed`؛ hierarchy authorization=`PASS`؛ Plan/Inbound=`14 assertions passed`؛ diff-check=`PASS`؛ Graphify=`4285/10950/456` و diagnose بدون dangling/duplicate؛ Browser دو بار=`Error: No browser is available` | screenshot قبل/بعد، viewport desktop/laptop، console و overflow واقعی=`NOT EXECUTED/BLOCKED` تا اتصال Browser؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-23` | Admin UX / `set-owner` / آماده‌سازی `v5.0.0-rc.3` | pre-publication gate=`PASS` | فرم ویرایش ادمین کنترل جداگانه افزایش/کاهش اعتبار با دلیل، تأیید reclaim و idempotency ثابت دارد؛ endpoint و ledger موجود حفظ شد؛ متن فارسی نقش روشن شد؛ alias واقعی `marzban set-owner USERNAME` در fork scripts منتشر شد؛ schema/migration/accounting behavior تغییر نکرد | main=`49c9e1d` + working tree؛ scripts=`4830af3566022502159935eeb8636f1af3148502` | backend/release contract=`10 passed`؛ Admin UX=`25 assertions`؛ hierarchy auth=`PASS`؛ Plan/Inbound=`14 assertions`؛ TypeScript/Vite=`1752 modules`؛ JSON/YAML/compile/diff/secret scan و سه shell contract=`PASS`؛ Graphify code update=`4297/13084` | commit/tag/prerelease `v5.0.0-rc.3` و انتظار CI/GHCR؛ Browser واقعی و direct CLI روی Windows=`NOT EXECUTED`؛ bundle warning و 11 zero-node Graphify=`UNCERTAINTY`؛ بدون deploy/final v5 |
| `2026-08-23` | انتشار `v5.0.0-rc.3` | `FAIL` در CI؛ tag/commit immutable حفظ شد | branch و tag منتشر شدند؛ تست Stage 9 هنوز محل قدیمی فیلد تماس را در `Admins.tsx` hard-code کرده، درحالی‌که refactor فیلد `type="tel"` را به `AdminFormDrawer.tsx` منتقل کرده است؛ application failure گزارش نشد | main/tag commit=`91461d7b1637589b8189b4fba4193fc8eb5f3849`؛ tag object=`ed32e1e27b29fff419506d0afe0fe56d607963a9` | workflow `32638997993`: volume-upgrade=`PASS`؛ MySQL 8.0/latest=`FAIL` با `1 failed, 213 passed, 1 skipped`؛ Docker build=`SKIPPED`؛ GHCR rc.3=`404`؛ GitHub Release=`NOT CREATED` | rc.3 بازنویسی نشود؛ test contract با ساختار جدید همسو و فقط پس از مجوز Owner کاندیدای بعدی ساخته شود؛ بدون deploy/final v5 |
| `2026-08-24` | Admin/Dashboard corrective slice | implementation/regression=`PASS`؛ MySQL live=`NOT EXECUTED` | مجوز/سهمیه سلسله‌مراتبی ساخت Admin، انتخاب صریح mode، `USER_CREDIT`، Owner unrestricted، Freeze/Trial reset، bulk mode-aware، فرم فشرده، Dashboard KPI/chart/quick access، theme مشکی–طلایی و branding logo؛ migration=`8b7d3e5f1a24` و دو index settings | `91461d7` + working tree؛ بدون commit | full=`215 passed, 9 skipped`؛ targeted جدید=`36 passed`؛ TypeScript/Vite/UI contract=`PASS` و `1775 modules`؛ Browser login در `375/768/1024/1440` بدون overflow و asset/console نسخه جدید=`PASS`؛ API چهار حساب demo=`PASS`؛ MySQL 8.x زنده در محیط موجود نبود؛ Graphify=`4365/11222/454` و diagnose بدون dangling/duplicate | preview روی `127.0.0.1:8000` باز بماند؛ migration production فقط روی clone امن MySQL 8.x؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-24` | Preview login repair | `PASS` | علت login خراب، build دستی بدون `VITE_BASE_API` بود و UI به `/admin/token` می‌رفت؛ fallback دائمی `/api/` در HTTP client/Core settings و build صحیح افزوده شد؛ modalهای زیرساخت فقط برای Owner mount می‌شوند تا فرزند درخواست غیرمجاز Node نفرستد | `91461d7` + working tree؛ بدون commit | Browser واقعی: Owner/Super/Admin خالی هر سه login=`200`؛ Owner dashboard مشکی–طلایی، Super بدون core و Admin بدون menu ادمین/کاربر=`0`؛ console نسخه `4d8ef5af` بدون error؛ TypeScript/Vite=`PASS`؛ Admin UX=`34 assertions` | مرورگر با `owner_demo` روی dashboard باز و preview server فعال بماند؛ بدون publication |
| `2026-08-24` | Admin UX regression repair final | `PASS` | فهرست و عملیات ادمین در یک سطح ادغام شد؛ فیلتر و عملیات گروهی فشرده و mode-aware شدند؛ Trial reset در سهمیهٔ پر دیگر انتقال صفر و HTTP 500 تولید نمی‌کند؛ Freeze دلیل اجباری فارسی دارد؛ `PLAN_ONLY` پیش‌فرض امن فرزند و جلوگیری از ارتقای مجوز اعمال شد؛ فرم‌های User/Plan/Audit/Device داخل viewport، مرحلهٔ دستگاه قابل حذف، گزارش فعالیت فارسی و Dashboard موبایل پیش‌فرض جمع‌شده است | `91461d7` + working tree؛ بدون commit | full backend=`217 passed, 9 skipped`؛ TypeScript=`PASS`؛ Admin UX contract=`PASS`؛ Vite production=`1773 modules` و asset `index.4e8e87b9.js`؛ compileall/diff-check=`PASS`؛ Browser واقعی desktop=`1440x900` modal=`top 12/bottom 888` و mobile=`375x812` بدون overflow، scroll height بسته=`2107`؛ Audit بدون متن event انگلیسی؛ API raw برای `admin_demo`=`403 plan_only` و create-from-plan=`PASS`؛ Graphify=`4380/11265/472` | preview روی `http://127.0.0.1:8000/dashboard/#/admins/` باز بماند؛ MySQL 8.x زنده/EXPLAIN در این محیط اجرا نشد؛ هیچ migration جدیدی در این برش نبود؛ بدون commit/push/tag/release/deploy/publish |
| `2026-08-24` | آماده‌سازی `v5.0.0-rc.4` | `AUTHORIZED / IN PROGRESS` | کاربر مجوز ارسال به GitHub و دریافت فرمان نصب/آپدیت داد؛ مقصد `smorad3363/Marzban` و احراز هویت `gh` تأیید شد؛ `rc.3` immutable حفظ و نسخه به `rc.4` افزایش یافت؛ فایل‌های محلی `.codex/`، `graphify-out/`، `design-system/` و دو حذف نامطمئن سند خارج manifest می‌مانند | `91461d7` + working tree | preflight remote/tag/auth=`PASS`؛ تست application همان برش=`217 passed, 9 skipped`؛ release contract و manifest gate در حال اجرا | اجرای release contract، secret/diff check، commit و push branch، tag immutable، انتظار CI/GHCR/Release؛ بدون deploy و بدون final `v5.0.0` |
| `2026-08-24` | انتشار `v5.0.0-rc.4` | `FAIL` در CI؛ tag immutable حفظ شد | branch و tag روی commit `0d41cf8` منتشر شدند؛ existing-volume upgrade=`PASS` ولی MySQL 8.0/latest در concurrency ledger نشان دادند Owner برای اعتبار محدود واگذارشده مقدار reconciliation را نگه نمی‌دارد؛ Docker/Release متوقف شد | `0d41cf8abc66875800efe090671bc855bb48dc03`؛ tag=`v5.0.0-rc.4` | Actions run=`32708807101`؛ MySQL assertion: `delegated_traffic 0 != 20`؛ image و GitHub Release=`NOT CREATED` | rc.4 بازنویسی نشود؛ tracking برای Owner محدود برگردد، `USED_TRAFFIC` همچنان actual-usage بماند؛ تست و انتشار immutable `rc.5` |
| `2026-08-24` | آماده‌سازی `v5.0.0-rc.5` | `PASS` برای pre-publication | Owner همچنان بدون سقف است، اما delegation محدود برای reconciliation ثبت می‌شود؛ والد `USED_TRAFFIC` از upfront delegation معاف و از مصرف واقعی فرزند شارژ می‌شود؛ قرارداد نسخه و مستندات به rc.5 افزایش یافت | `0d41cf8` + working tree | targeted=`26 passed`؛ full=`217 passed, 9 skipped`؛ release contract=`PASS`؛ Graphify=`4392/11275/471`؛ diff/secret/manifest gate پیش از commit تکرار می‌شود؛ MySQL CI گیت نهایی است | commit/push/tag rc.5؛ انتظار کامل CI/GHCR/Release؛ بدون deploy/final v5 |
| `2026-08-24` | انتشار `v5.0.0-rc.5` | `FAIL` در MySQL 8.0؛ tag immutable حفظ شد | credit reconciliation رفع و MySQL latest + existing-volume سبز شدند؛ MySQL 8.0 هنگام downgrade چون composite status index پشتیبان FK شده بود، در drop index با خطای `1553` متوقف شد؛ Docker/Release اجرا نشد | `103807f48960f9c14986464d042dff548506fb5b`؛ tag=`v5.0.0-rc.5` | Actions run=`32709664980`؛ MySQL latest=`PASS`؛ existing-volume=`PASS`؛ MySQL 8.0=`FAIL`؛ image/Release=`NOT CREATED` | rc.5 بازنویسی نشود؛ پیش از drop composite index، index تک‌ستونی FK بازسازی شود؛ انتشار rc.6 |
| `2026-08-24` | آماده‌سازی `v5.0.0-rc.6` | `PASS` برای pre-publication | downgrade MySQL ابتدا index تک‌ستونی `account_status_id` را در صورت نبود می‌سازد، سپس composite index را حذف می‌کند؛ FK و داده دست‌نخورده‌اند | `103807f` + working tree | migration/release targeted=`3 passed, 1 MySQL-local skipped`؛ compileall=`PASS`؛ full application از rc.5=`217 passed, 9 skipped`؛ Graphify=`4399/11282/473`؛ MySQL CI گیت نهایی | commit/push/tag rc.6 و انتظار CI/GHCR/Release؛ بدون deploy/final v5 |
| `2026-08-24` | اصلاح ذخیرهٔ mode و دسته‌های Plan ادمین | `PASS` | پاسخ canonical ویرایش ادمین فوراً در cache فهرست جایگزین شد؛ بازکردن سریع فرم دیگر `PLAN_ONLY` یا دسته‌های ذخیره‌شده را به مقدار قبلی برنمی‌گرداند؛ enforcement و حسابداری backend دست‌نخورده ماند | `3ca44d4` + working tree؛ بدون commit | frontend contract، TypeScript، hierarchy authorization، Plan/Inbound و Vite=`PASS`؛ targeted backend=`26 passed`؛ full backend=`219 passed, 9 skipped`؛ Browser save/reopen فوری mode و category=`PASS`؛ raw custom create=`403 plan_only` و plan create/accounting=`PASS` | schema/migration/API/query/dependency/version/install/update=`UNCHANGED`؛ MySQL زنده لازم/اجرا نشد چون DB path تغییر نکرد؛ بدون commit/push/tag/release/deploy |
| `2026-08-24` | بازیابی فهرست Admin و اکشن سریع اعتبار | `PASS` | credit محدود با `limit=0` بدون تقسیم بر صفر، exhausted و `100%` گزارش می‌شود؛ افزایش/کاهش mode-aware کنار Freeze در desktop/mobile با ledger موجود اضافه شد | `3ca44d4` + working tree؛ بدون commit | targeted backend=`7 passed`؛ full backend=`219 passed, 9 skipped`؛ Admin UX، hierarchy authorization، Plan/Inbound، TypeScript و Vite `1773 modules`=`PASS`؛ Browser list load و dialogهای grant/reclaim=`PASS`؛ رفت‌وبرگشت `0.01 GB`=`PASS` | schema/migration/query/index/dependency/version/install/update=`UNCHANGED`؛ MySQL live لازم/اجرا نشد؛ preview روی `127.0.0.1:8000` باز؛ بدون commit/push/tag/release/deploy |
| `2026-08-24` | رفع فریز Admin دستی و قدیمی | `PASS` | هر `SUSPENDED` دکمه رفع فریز دارد؛ Owner Freeze به `unfreeze` و suspension معمولی به `resume` می‌رود؛ eventless suspension فقط در نبود شرط فعال credit/expiry آزاد می‌شود | `3ca44d4` + working tree؛ بدون commit | targeted service=`3 passed`؛ full backend=`220 passed, 9 skipped`؛ Admin UX، TypeScript و Vite `1773 modules`=`PASS`؛ Browser واقعی `frozen_branch: SUSPENDED -> ACTIVE`=`PASS` و fixture بازگردانی شد | snapshot/eventهای Owner و accounting دست‌نخورده؛ schema/migration/dependency/version/install/update=`UNCHANGED`؛ preview باز؛ بدون commit/push/tag/release/deploy |
| `2026-08-24` | ترجمه محدودیت‌های Admin و فعال‌سازی `DISABLED` | `PASS` | پنج policy پیشرفته با برچسب/راهنمای فارسی؛ فعال‌سازی فقط account status توسط Owner/والد مجاز و بدون تغییر User/credit/Plan؛ برچسب رابطه «زیرمجموعهٔ» | `3ca44d4` + working tree؛ بدون commit | targeted=`5 passed`؛ full backend=`222 passed, 9 skipped`؛ Admin UX، JSON، TypeScript و Vite `1773 modules`=`PASS`؛ Browser ترجمه‌ها/دکمه/برچسب و console جدید بدون error=`PASS`؛ Graphify=`4408/11333/471` | schema/migration/query/index/dependency/version/install/update=`UNCHANGED`؛ MySQL live لازم/اجرا نشد؛ preview باز؛ بدون commit/push/tag/release/deploy |
| `2026-08-24` | عملیات سریع permission-aware داخل Dashboard | `PASS` | trigger چپ و بدون overlap؛ حذف اکشن‌های تکراری؛ ساخت Admin با `can_create_admins` و ساخت Plan با Owner/`can_manage_plans`؛ هر دو فرم inline و URL ثابت | `3ca44d4` + working tree؛ بدون commit | Admin UX=`PASS`؛ Plan/Inbound=`14 assertions`؛ hierarchy authorization، TypeScript و Vite `1773 modules`=`PASS`؛ Browser owner: overlap=`false`، دو dialog inline، URL ثابت و console=`0 error`؛ preview matrix Owner/Super/Admin=`PASS`؛ Graphify=`4414/11365/465` | backend/schema/migration/query/index/accounting/dependency/version/install/update=`UNCHANGED`؛ full backend تکرار نشد چون backend تغییر نکرد؛ بدون commit/push/tag/release/deploy |
| `2026-08-24` | بازطراحی داده‌محور Dashboard | `PASS` | چیدمان فشردهٔ مشکی–طلایی با خلاصهٔ mode-aware حساب، KPIهای scope-aware، وضعیت‌های انحصاری کاربران، پنج فعالیت آخر، نمودار چند-mode مشروط، منابع Owner-only و جزئیات جمع‌شوندهٔ موبایل؛ mountهای تکراری credit/statistics حذف شدند | `3ca44d4` + working tree؛ بدون commit | Admin UX، hierarchy authorization، Plan/Inbound، TypeScript و Vite `1773 modules`=`PASS`؛ Browser `375/768/812x375/1024/1440` بدون overflow، mobile scroll بسته=`1005`، console=`0 error`؛ role/API matrix Owner/Super/Admin=`PASS`؛ Graphify=`4424/11375/458` | API/schema/migration/query/index/accounting/permission/dependency/version/install/update=`UNCHANGED`؛ MySQL/SQL review از endpointهای bounded و queryهای موجود استفاده کرد و DB زنده لازم/اجرا نشد؛ preview باز؛ بدون commit/push/tag/release/deploy |
| `2026-08-24` | بازطراحی داده‌محور فهرست Admin | `PASS` | یک فهرست فشرده با چهار گروه دادهٔ غیرتکراری؛ status surface همراه badge متنی، progress صریح مصرف اعتبار، اکشن‌های permission-aware همان ردیف، secondary menu موبایل، filter/search بدون overlap و کارت موبایل بدون جدول افقی | `3ca44d4` + working tree؛ بدون commit | Admin UX، hierarchy authorization، Plan/Inbound و TypeScript=`PASS`؛ Vite=`1773 modules` و asset `index.0541cb66.js`؛ Browser `375/768/812x375/1024/1440` بدون overflow، filter/search overlap=`false`، menu/filter/details/credit-dialog/bulk-selection=`PASS` و console=`0 error`؛ Graphify=`4426/11377/454` | endpoint و query موجود `/admin-management` حفظ شد؛ backend/API/schema/migration/query/index/accounting/permission/dependency/version/install/update=`UNCHANGED`؛ MySQL زنده لازم/اجرا نشد؛ بدون commit/push/tag/release/deploy |
| `2026-08-25` | آماده‌سازی انتشار `v5.0.0-rc.7` | pre-publication local gate=`PASS` | نسخه runtime/contract/مستندات به rc.7؛ build نهایی با API نسبی `/api/` و asset `index.132a6776.js`؛ manifest فقط برش Admin/Dashboard تأییدشده و فایل‌های release | `3ca44d4` + working tree؛ بدون commit | full backend=`223 passed, 9 skipped`؛ release/API/Plan-only targeted=`13 passed`؛ Admin UX، hierarchy authorization و Plan/Inbound=`PASS`؛ TypeScript/Vite=`1773 modules`؛ compileall/diff-check=`PASS`؛ Graphify=`4432/11382/461` | schema/migration/query/index/dependency/install/update-script=`UNCHANGED`؛ MySQL محلی موجود نبود و CI روی 8.0/latest + existing-volume گیت نهایی است؛ manifest/secret review، commit/push/tag immutable، سپس تطبیق GitHub/GHCR؛ بدون deploy |
| `2026-08-25` | گیت parity پس از انتشار `v5.0.0-rc.7` و آماده‌سازی `rc.8` | `rc.7 CI=PASS`؛ updater parity=`FAIL` پیش از تحویل | commit/tag/CI/GHCR `rc.7` دقیق بودند؛ ریشهٔ اختلاف بالقوه regex پایدار-only در `marzban_script_ref` بود که برای prerelease اسکریپت را از `master` می‌گرفت؛ اصلاح محدود به پذیرش SemVer prerelease و bump immutable بعدی است | `a4045b87e89f33d62c79f00f837db9ac62d8558f` + working tree | Actions `32784403799` تمام jobها=`PASS`؛ GHCR digest rc.7/sha=`sha256:0aa58215d7e61981d85029c2eedaec3cd8a530114e81848f042ccebc6b201b79`؛ remote branch/tag peeled/CI head یکسان | تست contract updater و regression؛ انتشار immutable `v5.0.0-rc.8`؛ تطبیق نهایی؛ `rc.7` بازنویسی نشود و هیچ deploy اجرا نشود |
| `2026-08-25` | اصلاح install/update/bootstrap/build parity و آماده‌سازی `rc.9` | local gate=`PASS`؛ CI نهایی باز | SemVer prerelease در install، resolve جدیدترین release برای update بدون نسخه، ref یکسان script/files/image، پایان نصب بعد health، `create-owner` امن، قفل React/Chakra محلی، locale build ID مبتنی بر VERSION، CI build diff و رفع DOM number selection | `b1d88d7` + working tree | shell syntax/resolver=`PASS`؛ release/bootstrap=`2 passed`؛ Admin UX/hierarchy/Plan=`PASS`؛ TypeScript/Vite Node `20.19.5`=`1726 modules` و rebuild byte parity=`PASS`؛ YAML/diff-check=`PASS`؛ Graphify=`4454/11426/457` و diagnose clean؛ MySQL زنده=`NOT EXECUTED` | manifest/secret review؛ commit/push/tag immutable `v5.0.0-rc.9`؛ انتظار کامل CI/GHCR/Release؛ بدون deploy |
| `2026-08-25` | گیت `rc.9` و آماده‌سازی `rc.10` | `rc.9 CI=FAIL` فقط parity؛ سه DB=`PASS` | build source روی Linux hash متفاوت از Windows داشت؛ برای parity واقعی image، build source به `/tmp` منتقل و committed dashboard دست‌نخورده نگه داشته شد | `559b4cd` + working tree | Actions `32795337382`: MySQL 8.0/latest/existing-volume=`PASS`؛ Docker parity=`FAIL`؛ local isolated source build + committed immutability=`PASS` | انتشار immutable `rc.10` و انتظار CI/GHCR/Release؛ `rc.9` بازنویسی نشود؛ بدون deploy |
| `2026-08-25` | اصلاح `PLAN_ONLY` و بازیابی فهرست User؛ آماده‌سازی `rc.11` | local pre-publication gate=`PASS` | جلوگیری از commit شدن User بدون proxy؛ تحمل فقط در response برای ردیف خراب موجود؛ fail-closed شدن مجوز ساخت سفارشی و هدایت `PLAN_ONLY` به `/plans/`؛ build نسخه‌دار تازه | `7b6aaf2` + working tree؛ بدون commit | full backend=`226 passed, 9 skipped`؛ Admin UX/hierarchy/Plan=`PASS`؛ TypeScript=`PASS`؛ Vite Node `20.19.5` و rebuild 24 فایل byte-identical=`PASS`؛ Graphify=`4464/11445/467` | schema/migration/query/index=`UNCHANGED`؛ MySQL و SQL optimization review: رد زودهنگام یک write خراب را حذف می‌کند و ریسک migration ندارد؛ MySQL 8.0/latest/existing-volume در CI گیت نهایی؛ commit/push/tag/GHCR/Release immutable `rc.11`؛ بدون deploy |
| `2026-08-25` | بازگردانی فرم Admin به Modal وسط‌چین | local gate=`PASS`؛ publication=`NOT REQUESTED` | جایگزینی فقط wrapper `Drawer` با Chakra `Modal` وسط‌چین؛ scroll داخلی و footer ثابت؛ اصلاح جای دکمه بستن RTL؛ حذف dependency ناپایدار deep-link ساخت Admin | `04048b9` + working tree؛ بدون commit | Admin UX/hierarchy/Plan=`PASS`؛ TypeScript=`PASS`؛ Browser desktop `1440x900`: modal=`1024x876@208,12`، mobile `375x812`: modal=`351x788@12,12`، center delta=`0,0` و horizontal overflow=`false`؛ deep-link query پاک و dialog باز؛ Vite Node `20.19.5` asset=`index.788f4660.js` و rebuild 24 فایل byte-identical=`PASS`؛ Graphify=`4464/11445/466` | API/backend/schema/migration/query/index/accounting/dependency=`UNCHANGED`؛ در صورت درخواست صریح، bump و انتشار immutable بعدی؛ بدون deploy |
| `2026-08-25` | مهار بازگشت `PLAN_ONLY` به `FREE_FORM` | local gate=`PASS`؛ publication=`NOT REQUESTED` | root cause: migration عمداً hierarchy را تا اجرای `set-owner` خاموش نگه می‌دارد؛ capabilities در حالت sudo گزینه‌ها را نشان می‌داد، ولی create/modify فقط هنگام hierarchy فعال mode را ذخیره می‌کرد و default DB=`FREE_FORM` باقی می‌ماند. `hierarchy_enabled` به capabilities اضافه شد؛ UI هشدار و فرمان دقیق نشان می‌دهد و create/modify پیش از write با `409 admin_hierarchy_not_initialized` fail-closed می‌شوند | `04048b9` + working tree؛ بدون commit | regression create/modify و persistence=`3 passed`؛ مجموعه مرتبط backend=`19 passed` پیش از افزودن تست modify و targeted نهایی=`3 passed`؛ Admin UX=`PASS`؛ TypeScript=`PASS`؛ `git diff --check` فقط هشدار line-ending داشت | روی سرور `marzban set-owner saj` اجرا شود، سپس `asdad` دوباره روی `PLAN_ONLY` ذخیره شود؛ schema/migration/index جدید ندارد، داده production در این برش تغییر نکرد؛ بدون commit/push/tag/release/deploy |
| `2026-08-25` | شروع ساده‌سازی مدیر و سیاست read-only | `IN_PROGRESS` | نقش محصول فقط `OWNER/ADMIN` شد؛ API ساخت فرزند فقط `ADMIN` می‌پذیرد؛ گزینه و فیلتر نقش حذف شد؛ lookup قدیمی `SUPER_ADMIN` برای rollback در DB ماند و runtime آن را `ADMIN` می‌بیند | `04048b9` + working tree؛ بدون commit | role/service/plan/namespace targeted=`38 passed`؛ preflight Graphify/MySQL/SQL/UI=`PASS`؛ GitHub Release=`PASS`؛ `git ls-remote` DNS=`FAIL`؛ GHCR scope=`403` | افزودن lifetime metrics بدون N+1، سپس قفل Plan-only و suspended read-only؛ release-sensitive ممنوع |
| `2026-08-25` | تکمیل ساده‌سازی مدیر، lifetime و read-only | local gate=`PASS`؛ publication=`NOT REQUESTED` | فقط `OWNER/ADMIN`؛ فرم فشرده و بدون role/advanced accordion؛ lifetime consumed/created هم‌زمان و monotonic؛ قفل مستقیم quota برای `PLAN_ONLY` با Owner bypass؛ `SUSPENDED` دارای GET scope و mutation ممنوع؛ IP کامل همیشه فعال | `04048b9` + working tree؛ بدون commit | backend targeted=`61 passed`؛ Admin UX/hierarchy/Plan=`PASS`؛ TypeScript=`PASS`؛ Vite=`1773 modules`؛ Browser Modal Owner=`PASS` و console tab نهایی=`0 error` | Graphify update؛ سپس توقف تا دستور صریح انتشار؛ MySQL CI گیت نهایی و migration جدید=`0` |
| `2026-08-26` | لانچر تک‌دستوری Dev محلی | static gate=`PASS`؛ integration=`BLOCKED` | PowerShell ایزوله MySQL 8.0، Alembic، seed Owner/Admin/User/Plan، Backend واقعی با Xray/reload، Vite HMR، VS Code و مرورگر را راه‌اندازی می‌کند؛ seed فقط DB دقیق `marzban_dev@33079` را می‌پذیرد | `04048b9` + working tree؛ بدون commit | PowerShell parser=`PASS`؛ Python compile/import=`PASS`؛ DB guard safe/unsafe=`PASS`؛ Docker/MySQL/Xray=`NOT EXECUTED` چون Docker Desktop نصب نیست | نصب Docker Desktop؛ اجرای `powershell -ExecutionPolicy Bypass -File .\scripts\dev-local.ps1`؛ production/schema/migration/dependency/release=`UNCHANGED` |
| `2026-08-26` | رفع اجرای نخست لانچر Dev | integration=`PASS`؛ Dev روشن | probe image با `docker image ls --quiet`؛ pull صریح `mysql:8.0`؛ حذف `.test-*`/`.codex`/`graphify-out` از build context؛ `scripts/Dockerfile.dev` برای CRLF ویندوز؛ اجرای module-based seed؛ root صحیح Vite؛ URL دقیق `dashboard/index.html`؛ روش canonical Shadowsocks و repair idempotent داده نمونه | `04048b9` + working tree؛ بدون commit | PowerShell parser=`PASS`؛ image build=`PASS`؛ Alembic MySQL 8.0 تا `c2f4a8d6e913`=`PASS`؛ seed دوباره=`PASS`؛ MySQL=`healthy`؛ Frontend=`200`؛ Owner و سه Admin login=`PASS`؛ `/api/users` شش ردیف و `/api/admin-management` چهار ردیف=`PASS`؛ Browser Owner/Dashboard/User list و console=`PASS` | Dev روشن بماند؛ production/schema/migration/query/index/dependency/version/release=`UNCHANGED`؛ بدون commit/push/tag/release/deploy |
| `2026-08-26 10:44 +03:30` | آماده‌سازی `v5.0.0-rc.12` | local gate=`PASS` | نمایش «روش ساخت کاربر» از create/edit حذف شد؛ mapping canonical backend و payload حفظ شد؛ Owner در mode مصرف واقعی همچنان می‌تواند Plan/Trial بسازد؛ قیمت override هر reseller در پاسخ Plan و زنجیرهٔ خرید اعمال می‌شود و edit عادی Admin آن را پاک نمی‌کند؛ نسخه، build و release docs به rc.12 رسید | `04048b9` + working tree؛ بدون commit | frontend contracts=`PASS`؛ TypeScript/Vite=`1773 modules`؛ Browser create/edit بدون گزینه و console error=`PASS`؛ backend/migration/release targeted=`67 passed`؛ full discovery=`228 passed, 8 failed, 9 skipped` و failureهای سازگاری repair=`11 passed, 1 skipped`؛ money/trial/release retest=`16 passed, 1 skipped`؛ MySQL 8.0 head=`c2f4a8d6e913` و index/EXPLAIN=`PASS`؛ Graphify code-only=`4535/11226/509` | manifest/secret/diff review؛ commit/push/tag immutable rc.12؛ انتظار CI full/MySQL/GHCR/Release؛ سپس تست installer/update؛ بدون deploy |
| `2026-08-26` | گیت `rc.12` و آماده‌سازی `rc.13` | `rc.12 CI=FAIL` فقط downgrade MySQL 8.0؛ fix محلی=`PASS` | MySQL indexهای مرکب ledger را پشتیبان FK انتخاب کرد؛ downgrade پیش از drop table آن‌ها را دستی drop می‌کرد و با error `1553` شکست می‌خورد؛ drop دستی indexها حذف شد تا `DROP TABLE` خود MySQL همه index/FKهای همان جدول را اتمیک پاک کند | `4ccf813` + working tree | Actions `32943326038`: MySQL latest و existing-volume=`PASS`؛ MySQL 8.0 Stage8=`FAIL`؛ Docker/Release=`SKIPPED`؛ isolated MySQL 8.0 downgrade/re-upgrade پس از fix=`1 passed` | bump immutable `rc.13`؛ CI کامل/GHCR/Release؛ بدون deploy |
| `2026-09-04` | مرحلهٔ `0` نقشه‌راه اجرای Codex | `PASS` | تطبیق workspace/Git/ZIP و اسناد؛ تأیید انتشار `rc.13`، digestهای GHCR و rollback؛ تازه‌سازی Graphify روی HEAD؛ طبقه‌بندی findings و ساخت checkpoint فارسی/انگلیسی | `69e105fcebf627f0b9dfe588a9f7e3205767b01a` + working tree؛ بدون commit | `alembic heads`=`c2f4a8d6e913`؛ Graphify=`4869 nodes/12081 edges/516 communities`؛ بررسی ایستای هدفمند؛ full/backend/frontend/MySQL live=`NOT RUN` طبق scope مرحلهٔ `0` | `مرحله 1 را شروع کن`؛ بدون feature/schema/migration/commit/push/tag/release/deploy |
| `2026-09-04` | مرحلهٔ `1` نقشه‌راه اجرای Codex | `PASS` | حذف password از report؛ بستن self-edit تجاری Admin؛ Owner-only شدن Device Limit در backend/UI؛ منع activation عادی هنگام penalty و restore کنترل‌شدهٔ وضعیت قبلی | `69e105fcebf627f0b9dfe588a9f7e3205767b01a` + working tree؛ بدون commit | pre-fix=`12 failed, 5 passed`؛ backend هدفمند=`21 passed`؛ Admin UX contract=`PASS`؛ TypeScript=`PASS`؛ compileall=`PASS` | مرحلهٔ `2 — Host / Inbound / Plan Synchronization`؛ schema/migration/dependency/commit/push/tag/release/deploy=`UNCHANGED` |
| `2026-09-04` | آماده‌سازی انتشار پایدار `v5.1.0` | `IN_PROGRESS` | تکمیل مراحل `0` تا `7`؛ انتخاب نسخه بعد از `v5.0.0-rc.13`؛ جداسازی `.codex/` و `graphify-out/` از Git؛ ثبت release metadata | `69e105f` + working tree | backend=`275 passed, 9 skipped`؛ frontend build=`PASS`؛ MySQL migration/downgrade/re-upgrade و backup/restore=`PASS`؛ `git diff --check`=`PASS` | build همسان با Node 20؛ secret/staging review؛ commit/tag/push؛ انتظار CI و smoke نصب/update |

### گزارش DB پیش از انتشار `v5.0.0-rc.13`

- source: `v5.0.0-rc.12@4ccf813e66b93b870ca2034f87caad27e68b2abf`؛ target محلی: `v5.0.0-rc.13`.
- migration: `c2f4a8d6e913` روی `8b7d3e5f1a24`؛ چهار ستون مالی افزایشی، قیمت نسخهٔ Plan، جدول قیمت reseller و ledger immutable اضافه می‌شوند.
- MySQL: fresh Dev روی `mysql:8.0` تا head اجرا و seed idempotent پاس شد؛ production DB لمس نشد. matrix کامل 8.0/latest/existing-volume و backup/restore در CI release گیت نهایی است.
- index: ledger دارای `(admin_id, created_at, id)` و `(user_id, created_at, id)`؛ قیمت reseller دارای PK `(admin_id, plan_id)` و index معکوس `(plan_id, admin_id)` است.
- evidence: `EXPLAIN` آخرین تراکنش‌های Admin از `ix_admin_money_admin_created` با `type=ref` و backward index scan استفاده کرد؛ full scan دیده نشد.
- کارایی: debit/credit و history bounded از indexهای مرکب استفاده می‌کنند؛ delete User رکورد ledger را حذف نمی‌کند و شمارنده‌های lifetime monotonic می‌مانند.
- ریسک: DDL افزایشی و قابل downgrade است؛ پیش از update واقعی backup الزامی است. downgrade جدول‌های مالی و ستون‌های جدید را حذف می‌کند، پس rollback schema فقط با تصمیم اپراتور و backup انجام شود.

### گزارش DB انتشار `v5.0.0-rc.6`

- source: آخرین نسخهٔ قابل نصب پیش از این برش `v4.9.8@b45e3af663cd16d6dcca8492a6520b7e39db9d80`؛ target=`v5.0.0-rc.6@cee2c74ce520c503f9dd66847cc62aa93edd5062`.
- Alembic target head: `8b7d3e5f1a24`؛ migration جدید این اصلاح اضافه نشد و همان migration پیش از انتشار امن شد.
- engine: workflow روی `mysql:8.0` و `mysql:latest`، همراه مسیر existing-volume `8.0 → 8.4 → 9.7 → latest` موفق بود؛ semantic patch دقیق imageهای شناور در خروجی نهایی workflow چاپ نشد.
- backup/restore: گیت backup checksum/restore در job MySQL موفق بود؛ production backup path/checksum=`N/A` چون هیچ دیتابیس واقعی deploy یا migrate نشد.
- fresh/existing/partial-DDL/downgrade/re-upgrade: همگی در CI موفق؛ خطای قبلی MySQL `1553` با بازسازی index پشتیبان FK قبل از drop composite رفع شد.
- داده: هیچ row، ID، رابطهٔ Admin/User، credit، usage یا audit بازنویسی نشد؛ تغییر فقط ترتیب index DDL در downgrade است. row count و backfill برای این fix=`0`.
- کارایی: index مرکب `(account_status_id, admin_id)` در head حفظ می‌شود؛ downgrade فقط index تک‌ستونی لازم برای FK را برمی‌گرداند. full scan یا query جدید اضافه نشد.
- ریسک عملیاتی: پایین و محدود به downgrade؛ FK حذف/بازسازی نمی‌شود. update عادی فقط upgrade را اجرا می‌کند. پیش از update production همچنان backup اجباری است.
