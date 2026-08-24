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
assert.ok(drawer.includes('setQueriesData<ManagedAdminList | undefined>("admin-management"'), "saved Admin response must replace stale list cache before closing");
assert.ok(drawer.includes("item.id === savedAdmin.id ? savedAdmin : item"), "Admin cache update must use the canonical saved record");
assert.ok(drawer.includes('aria-pressed={form.user_creation_mode === creationMode}'), "user creation mode buttons must expose their selected state");
assert.ok(drawer.includes("تغییر سریع اعتبار"), "edit flow must expose a separate credit adjustment section");
assert.ok(drawer.includes('/credit/${operation}'), "credit adjustment must use the existing ledger endpoint");
assert.ok(drawer.includes("idempotency_key"), "credit adjustment must send an idempotency key");
assert.ok(!admins.includes("<Modal"), "legacy one-shot Admin modal must not remain");
assert.ok(admins.includes("<AdminFormDrawer"), "Admins page must use refactored drawer");
assert.ok(!admins.includes("<AdminHierarchyPanel"), "Admins page must not render a second competing hierarchy list");
assert.ok(admins.includes("colSpan={4}"), "Admin desktop list must stay limited to four purposeful data groups");
assert.ok(admins.includes("statusMeta[item.account_status].background"), "Admin rows must expose status with both text and a distinct surface");
assert.ok(admins.includes("مصرف اعتبار") && admins.includes("<Progress"), "credit summary must pair the remaining value with an explicit usage indicator");
assert.ok(admins.includes("renderMoreActions(item, true)"), "mobile Admin cards must keep secondary actions in a compact accessible menu");
assert.ok(admins.includes("فیلتر نوع اعتبار"), "Admin list must expose billing-mode filtering");
assert.ok(admins.includes('item.account_status === "SUSPENDED"'), "Admin freeze state must remain visible");
assert.ok(admins.includes("mixedSelection"), "bulk operations must reject mixed accounting resources");
assert.ok(admins.includes("trial-quota/reset"), "trial allowance reset must be an inline quick action");
assert.ok(admins.includes("freezeReason.trim()"), "manual freeze must require a human-readable reason");
assert.ok(admins.includes('item.account_status === "SUSPENDED"'), "every suspended Admin must expose an unfreeze action");
assert.ok(admins.includes('item.active_owner_freeze_event_id ? "unfreeze" : "resume"'), "unfreeze action must route owner freezes and manual suspensions correctly");
assert.ok(admins.includes('operation: "activate"'), "disabled Admins must expose an activation action");
assert.ok(admins.includes("زیرمجموعهٔ:"), "Admin relationship label must describe the child relationship");
for (const key of ["admins.preventCreate", "admins.preventDelete", "admins.preventReset", "admins.preventRevoke", "admins.preventUnlimited"]) {
  assert.ok(drawer.includes(key), `advanced Admin policy translation missing: ${key}`);
}
assert.ok(admins.includes('openCredit(item, "grant")'), "Admin rows must expose quick credit grant beside status actions");
assert.ok(admins.includes('openCredit(item, "reclaim")'), "Admin rows must expose quick credit reclaim beside status actions");
assert.ok(admins.includes("/credit/${operation}"), "quick credit actions must reuse the existing ledger endpoint");
assert.ok(admins.includes("filtersDisclosure.onToggle"), "Admin filters must be collapsed by default");

assert.ok(overview.includes("بازکردن دسترسی سریع"), "AssistiveTouch-style quick actions trigger missing");
assert.ok(overview.includes('left={{ base: 4, md: 6 }}'), "quick actions trigger must stay clear of the right sidebar branding controls");
assert.ok(!overview.includes('label="فهرست کاربران"'), "quick actions must not duplicate the Dashboard user list");
assert.ok(!overview.includes('label="مدیریت ادمین‌ها"'), "quick actions must not duplicate Admin navigation");
assert.ok(!overview.includes('label="پلن‌ها"'), "quick actions must not duplicate Plan navigation");
assert.ok(overview.includes('label="ساخت ادمین"') && overview.includes("capabilities.data?.can_create_admins"), "inline Admin creation must follow Admin capabilities");
assert.ok(overview.includes('label="ساخت پلن"') && overview.includes("canCreatePlan"), "inline Plan creation must follow Plan-management permission");
assert.ok(dashboard.includes("<AdminFormDrawer") && dashboard.includes("<PlanCreateModal"), "Dashboard quick-create forms must open in place");
assert.ok(overview.includes('<Chart type="bar"') && overview.includes('<Chart type="donut"'), "dashboard must include compact charts");
assert.ok(overview.includes('/account/activity?limit=5'), "dashboard recent activity must use the bounded cursor endpoint");
assert.ok(overview.includes('trafficModes.length > 1'), "billing-mode chart must stay hidden when it would add no comparison value");
assert.ok(overview.includes('enabled: Boolean(isOwner && account.data)'), "system metrics must only load for Owner");
assert.ok(overview.includes("mobileDetailsOpen") && overview.includes("نمایش نمودارها و فعالیت‌ها"), "mobile dashboard details must be collapsed behind an explicit control");
assert.ok(!dashboard.includes("<AdminCreditSummary") && !dashboard.includes("<Statistics"), "dashboard must not repeat account, user, or traffic summaries in legacy cards");
assert.ok(overview.includes('user_creation_mode === "FREE_FORM"'), "quick create-user action must follow creation mode");
assert.ok(userDialog.includes('user_creation_mode === "PLAN_ONLY"'), "user dialog must fail closed for Plan-only Admins");
assert.ok(userDialog.includes('insetInlineStart={3}'), "RTL modal close button must stay opposite the title");
assert.ok(userDialog.includes('my="3"'), "user modal must reserve top and bottom viewport margins");
assert.ok(deviceLimits.includes("removeStage"), "device penalty stages must be removable");
assert.ok(auditLogs.includes("localizeAction"), "audit actions must be localized");
assert.ok(auditLogs.includes("advancedFiltersOpen"), "audit advanced filters must be collapsible");
assert.ok(header.includes("mobileMenuOpen"), "mobile navigation must be collapsed by default");
assert.ok(dashboard.includes('holiday || "روز کاری"'), "dashboard must show Persian workday or holiday status");
assert.ok(overview.includes("منابع سرور"), "dashboard Owner resource group missing");
assert.ok(dashboard.includes("mobileUsersOpen") && dashboard.includes("نمایش کاربران"), "mobile user list must be collapsed behind an explicit toggle");
assert.ok(http.includes('import.meta.env.VITE_BASE_API || "/api/"'), "production login must retain the /api/ fallback");
assert.ok(dashboard.includes("{isOwner && ("), "Owner-only infrastructure dialogs must not query restricted APIs for children");

console.log("admin UX contract: assertions passed");
