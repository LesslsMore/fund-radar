import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
// 用 Node 22 内置的 node:sqlite, 避免原生二进制依赖 (better-sqlite3 无法跨平台打包)
import { DatabaseSync } from 'node:sqlite';
import { buildQuery, ITEM_SQL } from './_query.js';

export { buildQuery };

// 注意: 变量名不能叫 __dirname, Netlify 打包器会注入同名声明导致冲突
const LIB_DIR = path.dirname(fileURLToPath(import.meta.url));

// 兼容 Vercel 打包路径与本地 node 直跑两种情况
const CANDIDATES = [
  path.join(LIB_DIR, 'db', 'funds.db'),
  path.join(LIB_DIR, 'api', 'db', 'funds.db'),
  path.join(process.cwd(), 'api', 'db', 'funds.db'),
  path.join(process.cwd(), 'db', 'funds.db'),
];

// .vercelignore 上传时排除了 funds.db (太大导致本地上传不稳),
// 生产环境冷启动时从 GitHub raw 下载最新库(每日 Actions 自动更新)并缓存到 /tmp
const RAW_DB_URL = process.env.RAW_DB_URL ||
  'https://raw.githubusercontent.com/LesslsMore/fund-radar/main/api/db/funds.db';
const MAX_AGE_MS = 6 * 3600 * 1000; // /tmp 缓存超过 6 小时则重新下载

let _db = null;

async function resolveDbPath() {
  const local = CANDIDATES.find((c) => fs.existsSync(c));
  if (local) return local;

  const dest = path.join(os.tmpdir(), 'fund-radar-funds.db');
  const stale = fs.existsSync(dest) &&
    Date.now() - fs.statSync(dest).mtimeMs > MAX_AGE_MS;
  if (!fs.existsSync(dest) || stale) {
    const res = await fetch(RAW_DB_URL);
    if (!res.ok) throw new Error(`db download failed: HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    const tmp = dest + '.tmp';
    fs.writeFileSync(tmp, buf);
    fs.renameSync(tmp, dest);
  }
  return dest;
}

export async function getDb() {
  if (_db) return _db;
  const p = await resolveDbPath();
  _db = new DatabaseSync(p);
  _db.exec('PRAGMA query_only = 1');
  return _db;
}

export function ok(res, data, cacheSec = 300) {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', `public, max-age=${cacheSec}, s-maxage=${cacheSec}`);
  res.end(JSON.stringify({ code: 0, data, message: 'ok' }));
}

export function fail(res, status, message) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.end(JSON.stringify({ code: status, data: null, message }));
}

// ITEM_SQL / buildQuery 均来自 _query.js (三端共用), 在文件头部 import

// 查询参数 -> WHERE/ORDER BY: 见 _query.js (三端共用)

export async function runQuery(q = {}) {
  const db = await getDb();
  const { where, args, orderBy } = buildQuery(q);
  const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';
  const total = db.prepare(`SELECT COUNT(*) AS n FROM funds f LEFT JOIN returns r ON r.code=f.code LEFT JOIN risk k ON k.code=f.code ${whereSql}`).get(...args).n;

  let items;
  if (q.all === '1') {
    if (total > 20000) throw new Error('result too large for all=1');
    items = db.prepare(`${ITEM_SQL} ${whereSql} ORDER BY ${orderBy}`).all(...args);
  } else {
    const pageSize = Math.min(Math.max(parseInt(q.page_size || '50', 10) || 50, 1), 1000);
    const page = Math.max(parseInt(q.page || '1', 10) || 1, 1);
    items = db.prepare(`${ITEM_SQL} ${whereSql} ORDER BY ${orderBy} LIMIT ? OFFSET ?`)
      .all(...args, pageSize, (page - 1) * pageSize);
    return { items, total, page, page_size: pageSize };
  }
  return { items, total, page: 1, page_size: total };
}
