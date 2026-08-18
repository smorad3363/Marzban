# نقشه راه Owner، Super Admin، Admin، سلسله‌مراتب و انتقال اعتبار

آخرین به‌روزرسانی: `2026-08-19`

وضعیت: `V4.9.2_RELEASED` — schema، backend، API، CLI و UI پیاده و منتشر شدند. migration تازه/قدیمی/partial-DDL، backup/checksum/restore و rollback برنامه `v4.8.0` روی MySQL 8.0 موفق‌اند. تا تعیین Owner، رفتار اجرایی قدیمی `is_sudo` حفظ می‌شود.

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
9. هر گزارش پیشرفت دارای تغییر DB باید نتیجه بررسی سازگاری upgrade، backfill داده قدیمی و rollback application را به کاربر نشان دهد.

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

هر نسخه جدید باید با دستور update موجود Marzban از تمام وضعیت‌های DB پشتیبانی‌شده بالا بیاید؛ چه دیتابیس خالی باشد، چه داده قدیمی/ناقص داشته باشد. موفق‌بودن فقط روی DB توسعه قابل قبول نیست.

### ماتریس الزامی آزمون Upgrade

- نصب تازه با DB خالی تا Alembic head جدید.
- DB آخرین tag قابل‌نصب تا head جدید.
- DB تمام releaseهای پشتیبانی‌شده‌ای که schema را تغییر داده‌اند تا head جدید.
- حداقل snapshot قدیمی canonical از `v4.0.0` تا نسخه هدف.
- DB دارای Admin/User/credit/usage/template/node واقعی و مقدارهای `NULL` قدیمی.
- DB با migration نیمه‌اجراشده MySQL و DDL جزئی.
- اجرای دوباره migration پس از قطع سرویس یا برق.
- اجرای image نسخه rollback روی schema جدید؛ چون rollback فعلی migration دیتابیس را downgrade نمی‌کند.

release تا موفقیت همه حالت‌های مرتبط منتشر نشود. برای هر مسیر، تعداد ردیف، شناسه‌ها، ownership، جمع credit/usage و hash یا snapshot داده حساس بررسی شود.

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

هر لاگ پیشرفت migration باید این اطلاعات را نشان دهد:

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
- migration جدید قبل از release روی snapshot تمام schemaهای پشتیبانی‌شده و DB خالی اجرا شود.
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

پیاده‌سازی و انتشار کامل است. tag `v4.9.2` روی commit `ded182ec2f50b3fe553752947eff27be7912c83e` قرار دارد؛ GitHub Actions run `32196890824` موفق شد؛ Release دارای نشان Latest است؛ imageهای `v4.9.2`، `latest` و `sha-ded182ec2f50` همگی digest برابر `sha256:c0fdbfb7c4af7b2360ca8718c83f20ccf4dca7534fa38becb550e81bd6096973` دارند. tagهای ناموفق `v4.9.0` و `v4.9.1` برای حفظ تاریخچه جابه‌جا یا حذف نشدند. قدم عملیاتی بعدی فقط backup دیتابیس واقعی و update/install کنترل‌شده `v4.9.2` است.

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
