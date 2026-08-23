const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8");

const drawer = read("src/components/AdminFormDrawer.tsx");
const admins = read("src/pages/Admins.tsx");
const hierarchy = read("src/components/AdminHierarchyPanel.tsx");
const dashboard = read("src/pages/Dashboard.tsx");
const overview = read("src/components/DashboardOverview.tsx");

for (const section of [
  "مشخصات ادمین",
  "نوع اعتبار",
  "محدودیت‌ها",
  "دسترسی‌ها",
  "تنظیمات بیشتر",
]) {
  assert.ok(drawer.includes(section), `missing admin step: ${section}`);
}

assert.ok(drawer.includes("h=\"100dvh\""), "drawer must use dynamic viewport height");
assert.ok(drawer.includes("maxH=\"100dvh\""), "drawer must cap dynamic viewport height");
assert.ok(drawer.includes("overflow=\"hidden\""), "drawer shell must contain overflow");
assert.ok(drawer.includes("overflowY=\"auto\""), "drawer body must scroll independently");
assert.ok(drawer.includes("minH={0}"), "drawer body must be shrinkable inside flex shell");
assert.ok(drawer.includes("<DrawerFooter"), "drawer actions must live in persistent footer");
assert.ok(drawer.includes("<Accordion allowMultiple"), "advanced options must be collapsed by default");
assert.ok(drawer.includes("افزایش یا کاهش اعتبار"), "edit flow must expose a separate credit adjustment section");
assert.ok(drawer.includes('/credit/${operation}'), "credit adjustment must use the existing ledger endpoint");
assert.ok(drawer.includes("idempotency_key"), "credit adjustment must send an idempotency key");
assert.ok(!admins.includes("<Modal"), "legacy one-shot Admin modal must not remain");
assert.ok(admins.includes("<AdminFormDrawer"), "Admins page must use refactored drawer");
assert.ok(admins.includes("colSpan={5}"), "secondary desktop columns must move into details row");
assert.ok(hierarchy.includes("اعتبار گروهی"), "bulk credit area must remain available");
assert.ok(hierarchy.includes("expandedAdminId"), "per-admin operations must use progressive disclosure");

for (const group of ["آمار کلی", "این هفته", "نوع اعتبار"]) {
  assert.ok(overview.includes(group), `missing dashboard group: ${group}`);
}
assert.ok(dashboard.includes("کاربران"), "dashboard quick actions group missing");
assert.ok(dashboard.includes("وضعیت سرور"), "dashboard system group missing");

console.log("admin UX contract: 25 assertions passed");
