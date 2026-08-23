const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const sourcePath = path.resolve(
  __dirname,
  "../src/utils/adminHierarchyAuthorization.ts"
);
const output = ts.transpileModule(fs.readFileSync(sourcePath, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;
const testModule = { exports: {} };
vm.runInNewContext(output, { exports: testModule.exports, module: testModule });
const { canManageHierarchyNode } = testModule.exports;

const owner = { id: 1, role: "OWNER" };
const parent = { id: 2, role: "SUPER_ADMIN" };
const outsider = { id: 3, role: "SUPER_ADMIN" };
const child = { id: 4, parent_admin_id: 2 };

assert.equal(canManageHierarchyNode(owner, child), true);
assert.equal(canManageHierarchyNode(parent, child), true);
assert.equal(canManageHierarchyNode(outsider, child), false);
assert.equal(canManageHierarchyNode(child, child), false);

console.log("admin hierarchy authorization: PASS");
