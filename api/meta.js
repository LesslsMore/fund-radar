import { ok, fail, getDb } from './_lib.js';

// GET /api/meta -> 数据日期/构建时间/各分组数量
export default async function handler(req, res) {
  try {
    const db = getDb();
    const meta = Object.fromEntries(
      db.prepare('SELECT key, value FROM meta').all().map((r) => [r.key, r.value])
    );
    const byGroup = db.prepare(
      `SELECT limit_group AS g, COUNT(*) AS n, 
              SUM(CASE WHEN sgzt='开放申购' THEN 1 ELSE 0 END) AS open_n,
              SUM(CASE WHEN sgzt='限大额' THEN 1 ELSE 0 END) AS big_n
       FROM funds WHERE is_bond = 1 GROUP BY limit_group`
    ).all();
    const byType = db.prepare(
      `SELECT type, COUNT(*) AS n FROM funds WHERE is_bond = 1 GROUP BY type ORDER BY n DESC`
    ).all();
    ok(res, { ...meta, bond_by_group: byGroup, bond_by_type: byType }, 300);
  } catch (e) {
    fail(res, 500, e.message || 'error');
  }
}
