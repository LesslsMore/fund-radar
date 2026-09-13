// vercel build 后清洗函数包 .vc-config.json 里对 funds.db 的追踪引用
// (nft 静态追踪把被 .vercelignore 排除的 db 记进了 filePathMap, 平台部署时 lstat 会失败)
// 用法: vercel build --prod && node scripts/fix-vcconfig.mjs && vercel deploy --prebuilt --prod
import fs from "node:fs";
import path from "node:path";

const OUT = path.join(process.cwd(), ".vercel", "output", "functions");
let cleaned = 0;

function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (e.name === ".vc-config.json") {
      const cfg = JSON.parse(fs.readFileSync(p, "utf-8"));
      if (cfg.filePathMap) {
        for (const k of Object.keys(cfg.filePathMap)) {
          if (k.includes("funds.db")) {
            delete cfg.filePathMap[k];
            cleaned++;
          }
        }
        if (Object.keys(cfg.filePathMap).length === 0) delete cfg.filePathMap;
        fs.writeFileSync(p, JSON.stringify(cfg));
      }
    }
  }
}

walk(OUT);
console.log(`cleaned ${cleaned} funds.db references from vc-config files`);
