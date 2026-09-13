// Pages Functions: GET /api/meta
import { jsonEnvelope } from './_query.js';

export async function onRequestGet({ env }) {
  try {
    const db = env.DB;
    const metaRows = await db.prepare("SELECT key, value FROM meta").all();
    const meta = Object.fromEntries(metaRows.results.map((r) => [r.key, r.value]));
    const byGroup = (await db.prepare(
      `SELECT limit_group AS g, COUNT(*) AS n,
              SUM(CASE WHEN sgzt='开放申购' THEN 1 ELSE 0 END) AS open_n,
              SUM(CASE WHEN sgzt='限大额' THEN 1 ELSE 0 END) AS big_n
       FROM funds WHERE is_bond = 1 GROUP BY limit_group`
    ).all()).results;
    const byType = (await db.prepare(
      "SELECT type, COUNT(*) AS n FROM funds WHERE is_bond = 1 GROUP BY type ORDER BY n DESC"
    ).all()).results;
    return jsonEnvelope({ code: 0, data: { ...meta, bond_by_group: byGroup, bond_by_type: byType } });
  } catch (e) {
    return jsonEnvelope({ code: 500, data: null, message: e.message || "error" }, 500);
  }
}
