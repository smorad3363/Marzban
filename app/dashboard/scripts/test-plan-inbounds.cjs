const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

const sourcePath = path.resolve(__dirname, "../src/utils/planInbounds.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const plansSource = fs.readFileSync(
  path.resolve(__dirname, "../src/pages/Plans.tsx"),
  "utf8"
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    strict: true,
  },
});
const loaded = { exports: {} };
new Function("exports", "module", "require", compiled.outputText)(
  loaded.exports,
  loaded,
  require
);

const {
  collectPlanInboundOptions,
  missingPlanInboundTags,
  missingPlanHostIds,
  normalizePlanInboundTags,
  normalizePlanHostScope,
  togglePlanHostId,
  togglePlanInboundTag,
} = loaded.exports;

const configured = new Map([
  ["vless", [
    { tag: "vless-reality", protocol: "vless", network: "tcp", tls: "reality", port: 443 },
    { tag: "vless-ws", protocol: "vless", network: "ws", tls: "tls", port: 8443 },
  ]],
  ["vmess", [
    { tag: "vmess-ws", protocol: "vmess", network: "ws", tls: "none", port: 80 },
    { tag: "vless-ws", protocol: "vless", network: "ws", tls: "tls", port: 8443 },
  ]],
]);

const options = collectPlanInboundOptions(configured);
assert.deepEqual(options.map(({ tag }) => tag), ["vless-reality", "vless-ws", "vmess-ws"]);

let selected = togglePlanInboundTag([], "vless-ws", true);
assert.deepEqual(selected, ["vless-ws"]);
selected = togglePlanInboundTag(selected, "vmess-ws", true);
assert.deepEqual(selected, ["vless-ws", "vmess-ws"]);
selected = togglePlanInboundTag(selected, "vless-ws", true);
assert.deepEqual(selected, ["vless-ws", "vmess-ws"]);

const restored = normalizePlanInboundTags(["removed-legacy", "vless-ws", "vless-ws"]);
assert.ok(Array.isArray(restored));
assert.deepEqual(restored, ["removed-legacy", "vless-ws"]);
assert.deepEqual(missingPlanInboundTags(restored, options), ["removed-legacy"]);

const explicitRemoval = togglePlanInboundTag(restored, "removed-legacy", false);
assert.deepEqual(explicitRemoval, ["vless-ws"]);
assert.deepEqual(missingPlanInboundTags(explicitRemoval, options), []);

let hosts = normalizePlanHostScope({ "vless-ws": [9, 2, 9] });
assert.deepEqual(hosts, { "vless-ws": [2, 9] });
hosts = togglePlanHostId(hosts, "vless-ws", 4, true);
assert.deepEqual(hosts, { "vless-ws": [2, 4, 9] });
hosts = togglePlanHostId(hosts, "vless-ws", 2, false);
assert.deepEqual(hosts, { "vless-ws": [4, 9] });
assert.deepEqual(
  missingPlanHostIds(hosts, [{ tag: "vless-ws", hosts: [{ id: 4 }] }]),
  [9]
);

assert.equal(source.includes('.split(",")'), false);
assert.equal(source.includes('.join(",")'), false);
assert.match(plansSource, /inbounds:\s*string\[\]/);
assert.match(plansSource, /inbounds:\s*normalizePlanInboundTags\(draft\.inbounds\)/);
assert.match(plansSource, /hosts:\s*normalizePlanHostScope\(draft\.hosts\)/);
assert.match(plansSource, /حداقل یک Inbound/);
assert.equal(/draft\.inbounds\.(split|join)\(/.test(plansSource), false);
console.log("plan inbound selection: 14 assertions passed");
