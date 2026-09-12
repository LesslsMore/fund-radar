// Netlify Functions v2: GET /api/funds/:code
import { getDb } from '../../api/_lib.js';

export const config = { path: "/api/funds/:code" };

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": `public, max-age=600, s-maxage=600`,
    },
  });
}

export default async (req) => {
  try {
    const code = String(new URL(req.url).pathname.split("/").pop() || "")
      .replace(/[^0-9a-zA-Z]/g, "")
      .slice(0, 6);
    if (!code) return json({ code: 400, data: null, message: "invalid code" }, 400);
    const db = await getDb();
    const item = db.prepare(
      `SELECT f.*, r.w, r.m1, r.m3, r.m6, r.y1, r.y2, r.y3, r.ytd, r.since, r.source AS ret_source,
              k.sharpe_1y, k.sharpe_2y, k.sharpe_3y, k.std_1y, k.std_2y, k.std_3y, k.as_of
       FROM funds f
       LEFT JOIN returns r ON r.code = f.code
       LEFT JOIN risk k ON k.code = f.code
       WHERE f.code = ?`
    ).get(code);
    if (!item) return json({ code: 404, data: null, message: "fund not found" }, 404);
    return json({ code: 0, data: item });
  } catch (e) {
    return json({ code: 500, data: null, message: e.message || "error" }, 500);
  }
};
