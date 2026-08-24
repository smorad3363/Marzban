const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8");

const drawer = read("src/components/AdminFormDrawer.tsx");
const admins = read("src/pages/Admins.tsx");
const dashboard = read("src/pages/Dashboard.tsx");
const overview = read("src/components/DashboardOverview.tsx");
const userDialog = read("src/components/UserDialog.tsx");
const deviceLimits = read("src/pages/DeviceLimits.tsx");
const auditLogs = read("src/pages/AuditLogs.tsx");
const header = read("src/components/Header.tsx");
const http = read("src/service/http.ts");

for (const section of ["مشخصات", "نوع حساب", "اجازه ساخت ادمین", "محدودیت‌های اختیاری", "پلن‌ها و محدوده دسترسی", "گزینه‌های پیشرفته"]) {
  assert.ok(drawer.includes(section), `missing compact admin section: ${section}`);
}
assert.ok(drawer.includes("h=\"100dvh\""), "drawer must use dynamic viewport height");
assert.ok(drawer.includes("overflowY=\"auto\""), "drawer body must scroll independently");
assert.ok(drawer.includes("<DrawerFooter"), "drawer actions must live in persistent footer");
assert.ok(drawer.includes("<Accordion allowMultiple"), "advanced options must be collapsed by default");
assert.ok(drawer.includes('type="tel"'), "optional phone field must remain a telephone field");
assert.ok(drawer.includes("^09\\d{9}$"), "phone validation must require 09xxxxxxxxx when supplied");
assert.ok(drawer.includes('useState<BillingMode | "">("")'), "new Admin billing mode must have no implicit default");
assert.ok(!drawer.includes('<option value="LEGACY_COMPAT"'), "legacy compatibility mode must be hidden from fresh creation");
assert.ok(drawer.includes("تعداد اکانت قابل ساخت"), "user-credit mode must use an account-count label");
assert.ok(drawer.includes("اجازه واگذاری این دسترسی"), "delegated Admin creation must be explicit");
assert.ok(drawer.includes('user_creation_mode: "PLAN_ONLY"'), "new Admins must default to Plan-only user creation");
assert.ok(drawer.includes("ساخت سفارشی"), "free-form user creation must remain an explicit delegated option");
assert.ok(drawer.includes("تغییر سریع اعتبار"), "edit flow must expose a separate credit adjustment section");
assert.ok(drawer.includes('/credit/${operation}'), "credit adjustment must use the existing ledger endpoint");
assert.ok(drawer.includes("idempotency_key"), "credit adjustment must send an idempotency key");
assert.ok(!admins.includes("<Modal"), "legacy one-shot Admin modal must not remain");
assert.ok(admins.includes("<AdminFormDrawer"), "Admins page must use refactored drawer");
assert.ok(!admins.includes("<AdminHierarchyPanel"), "Admins page must not render a second competing hierarchy list");
assert.ok(admins.includes("colSpan={5}"), "secondary desktop columns must move into details row");
assert.ok(admins.includes("فیلتر نوع اعتبار"), "Admin list must expose billing-mode filtering");
assert.ok(admins.includes('item.account_status === "SUSPENDED"'), "Admin freeze state must remain visible");
assert.ok(admins.includes("mixedSelection"), "bulk operations must reject mixed accounting resources");
assert.ok(admins.includes("trial-quota/reset"), "trial allowance reset must be an inline quick action");
assert.ok(admins.includes("freezeReason.trim()"), "manual freeze must require a human-readable reason");
assert.ok(admins.includes("filtersDisclosure.onToggle"), "Admin filters must be collapsed by default");

assert.ok(overview.includes("بازکردن دسترسی سریع"), "AssistiveTouch-style quick actions trigger missing");
assert.ok(overview.includes('<Chart type="bar"') && overview.includes('<Chart type="donut"'), "dashboard must include compact charts");
assert.ok(overview.includes("can_manage_admins"), "dashboard actions must follow capabilities");
assert.ok(overview.includes('user_creation_mode === "FREE_FORM"'), "quick create-user action must follow creation mode");
assert.ok(userDialog.includes('user_creation_mode === "PLAN_ONLY"'), "user dialog must fail closed for Plan-only Admins");
assert.ok(userDialog.includes('insetInlineStart={3}'), "RTL modal close button must stay opposite the title");
assert.ok(userDialog.includes('my="3"'), "user modal must reserve top and bottom viewport margins");
assert.ok(deviceLimits.includes("removeStage"), "device penalty stages must be removable");
assert.ok(auditLogs.includes("localizeAction"), "audit actions must be localized");
assert.ok(auditLogs.includes("advancedFiltersOpen"), "audit advanced filters must be collapsible");
assert.ok(header.includes("mobileMenuOpen"), "mobile navigation must be collapsed by default");
assert.ok(dashboard.includes('holiday || "روز کاری"'), "dashboard must show Persian workday or holiday status");
assert.ok(dashboard.includes("وضعیت سرور"), "dashboard system group missing");
assert.ok(dashboard.includes("mobileUsersOpen") && dashboard.includes("نمایش کاربران"), "mobile user list must be collapsed behind an explicit toggle");
assert.ok(http.includes('import.meta.env.VITE_BASE_API || "/api/"'), "production login must retain the /api/ fallback");
assert.ok(dashboard.includes("{isOwner && ("), "Owner-only infrastructure dialogs must not query restricted APIs for children");

console.log("admin UX contract: assertions passed");
