// Netlify Functions v2: GET /api/meta
import { getDb } from '../../api/_lib.js';

export const config = { path: "/api/meta" };

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": `public, max-age=300, s-maxage=300`,
    },
  });
}

export default async (req) => {
  try {
    const db = await getDb();
    const meta = Object.fromEntries(
      db.prepare("SELECT key, value FROM meta").all().map((r) => [r.key, r.value])
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
    return json({ code: 0, data: { ...meta, bond_by_group: byGroup, bond_by_type: byType } });
  } catch (e) {
    return json({ code: 500, data: null, message: e.message || "error" }, 500);
  }
};
