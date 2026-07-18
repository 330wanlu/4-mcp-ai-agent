/**
 * 阶段 6：前端契约冒烟（不启浏览器）。
 * 检查源码包含三条用户故事与关键 API 调用点，且 Vite 构建产物可用。
 */
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const srcApp = readFileSync(join(root, "src", "App.tsx"), "utf8");
const srcApi = readFileSync(join(root, "src", "api.ts"), "utf8");
const srcTypes = readFileSync(join(root, "src", "types.ts"), "utf8");

const checks = [
  ["story qa text", srcTypes.includes("试用期员工年假怎么算")],
  ["story compare text", srcTypes.includes("差旅制度和报销制度分别管什么")],
  ["story action text", srcTypes.includes("起草一趟上海出差申请")],
  ["api createSession", srcApi.includes("/chat/sessions")],
  ["api postMessage", srcApi.includes("/messages")],
  ["api confirm", srcApi.includes("/confirm")],
  ["api reject", srcApi.includes("/reject")],
  ["api pending", srcApi.includes("pending-actions")],
  ["ui citations tab", srcApp.includes("引用")],
  ["ui trace tab", srcApp.includes("轨迹")],
  ["ui pending tab", srcApp.includes("待确认")],
  ["dev user header", srcApi.includes("X-User-Id")],
];

let failed = 0;
for (const [name, ok] of checks) {
  console.log(`${ok ? "OK" : "FAIL"}  ${name}`);
  if (!ok) failed += 1;
}

const distIndex = join(root, "dist", "index.html");
if (existsSync(distIndex)) {
  console.log("OK  dist/index.html exists");
  const assets = join(root, "dist", "assets");
  if (existsSync(assets) && readdirSync(assets).length > 0) {
    console.log("OK  dist/assets nonempty");
  } else {
    console.log("FAIL  dist/assets empty");
    failed += 1;
  }
} else {
  console.log("WARN dist not built yet (run npm run build)");
}

console.log(failed === 0 ? "SMOKE_EXIT=0" : "SMOKE_EXIT=1");
process.exit(failed === 0 ? 0 : 1);
