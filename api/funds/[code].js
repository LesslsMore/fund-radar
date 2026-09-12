import { ok, fail, getDb } from '../_lib.js';

// GET /api/funds/006431  -> 单只基金完整记录
export default async function handler(req, res) {
  try {
    const code = String(req.url.split('/').pop() || '').replace(/[^0-9a-zA-Z]/g, '').slice(0, 6);
    if (!code) return fail(res, 400, 'invalid code');
    const db = getDb();
    const item = db.prepare(
      `SELECT f.*, r.w, r.m1, r.m3, r.m6, r.y1, r.y2, r.y3, r.ytd, r.since, r.source AS ret_source,
              k.sharpe_1y, k.sharpe_2y, k.sharpe_3y, k.std_1y, k.std_2y, k.std_3y, k.as_of
       FROM funds f
       LEFT JOIN returns r ON r.code = f.code
       LEFT JOIN risk k ON k.code = f.code
       WHERE f.code = ?`
    ).get(code);
    if (!item) return fail(res, 404, 'fund not found');
    ok(res, item, 600);
  } catch (e) {
    fail(res, 500, e.message || 'error');
  }
}
