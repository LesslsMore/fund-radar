// D1 版查询执行: 与 api/_lib.js 的 runQuery 行为一致, 但跑在 Cloudflare D1 上
import { buildQuery, ITEM_SQL } from './_query.js';

export async function runQuery(db, q = {}) {
  const { where, args, orderBy } = buildQuery(q);
  const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';
  const total = (await db
    .prepare(`SELECT COUNT(*) AS n FROM funds f LEFT JOIN returns r ON r.code=f.code LEFT JOIN risk k ON k.code=f.code ${whereSql}`)
    .bind(...args)
    .first()).n;

  if (q.all === '1') {
    if (total > 20000) throw new Error('result too large for all=1');
    const items = (await db.prepare(`${ITEM_SQL} ${whereSql} ORDER BY ${orderBy}`).bind(...args).all()).results;
    return { items, total, page: 1, page_size: total };
  }
  const pageSize = Math.min(Math.max(parseInt(q.page_size || '50', 10) || 50, 1), 1000);
  const page = Math.max(parseInt(q.page || '1', 10) || 1, 1);
  const items = (await db
    .prepare(`${ITEM_SQL} ${whereSql} ORDER BY ${orderBy} LIMIT ? OFFSET ?`)
    .bind(...args, pageSize, (page - 1) * pageSize)
    .all()).results;
  return { items, total, page, page_size: pageSize };
}
