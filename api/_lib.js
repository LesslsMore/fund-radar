import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 兼容 Vercel 打包路径与本地 node 直跑两种情况
const CANDIDATES = [
  path.join(__dirname, 'db', 'funds.db'),
  path.join(__dirname, 'api', 'db', 'funds.db'),
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
  _db = new Database(p, { readonly: true, fileMustExist: true });
  _db.pragma('query_only = 1');
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

export const ITEM_SQL = `
SELECT
  f.code, f.name, f.type, f.sgzt, f.shzt, f.next_open_day,
  f.min_buy, f.daily_limit, f.limit_group, f.limit_display,
  f.fee_rate, f.nav, f.nav_date, f.is_bond,
  r.w, r.m1, r.m3, r.m6, r.y1, r.y2, r.y3, r.ytd, r.since, r.source AS ret_source,
  k.sharpe_1y, k.sharpe_2y, k.sharpe_3y, k.std_1y, k.std_2y, k.std_3y, k.as_of
FROM funds f
LEFT JOIN returns r ON r.code = f.code
LEFT JOIN risk k ON k.code = f.code
`;

// 查询参数 -> WHERE/ORDER BY (全部白名单, 无注入面)
export function buildQuery(q = {}) {
  const where = [];
  const args = [];
  const scope = q.scope === 'all' ? 'all' : 'bond';
  if (scope === 'bond') where.push('f.is_bond = 1');
  if (q.group && ['limited', 'unlimited', 'nodata'].includes(q.group)) {
    where.push('f.limit_group = ?');
    args.push(q.group);
  }
  if (q.status) {
    where.push('f.sgzt = ?');
    args.push(String(q.status).slice(0, 20));
  }
  if (q.type) {
    where.push('f.type LIKE ?');
    args.push(`%${String(q.type).slice(0, 30)}%`);
  }
  if (q.q) {
    const kw = `%${String(q.q).slice(0, 30).replace(/[%_]/g, '')}%`;
    where.push('(f.name LIKE ? OR f.code LIKE ?)');
    args.push(kw, kw);
  }
  const SORTS = {
    default: 'f.sort_order ASC, f.code ASC',
    limit_asc: '(f.daily_limit IS NULL) ASC, f.daily_limit ASC, f.code ASC',
    limit_desc: '(f.daily_limit IS NULL) DESC, f.daily_limit DESC, f.code ASC',
    y1_desc: '(CAST(NULLIF(r.y1,\'\') AS REAL) IS NULL) ASC, CAST(NULLIF(r.y1,\'\') AS REAL) DESC, f.code ASC',
    y1_asc: '(CAST(NULLIF(r.y1,\'\') AS REAL) IS NULL) ASC, CAST(NULLIF(r.y1,\'\') AS REAL) ASC, f.code ASC',
    sharpe_desc: '(CAST(NULLIF(k.sharpe_1y,\'\') AS REAL) IS NULL) ASC, CAST(NULLIF(k.sharpe_1y,\'\') AS REAL) DESC, f.code ASC',
  };
  const orderBy = SORTS[q.sort] || SORTS.default;
  return { where, args, orderBy, scope };
}

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
