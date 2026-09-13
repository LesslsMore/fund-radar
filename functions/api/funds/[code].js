// Pages Functions: GET /api/funds/:code
import { jsonEnvelope } from '../_query.js';

export async function onRequestGet({ env, params }) {
  try {
    const code = String(params.code || "").replace(/[^0-9a-zA-Z]/g, "").slice(0, 6);
    if (!code) return jsonEnvelope({ code: 400, data: null, message: "invalid code" }, 400);
    const item = await env.DB.prepare(
      `SELECT f.*, r.w, r.m1, r.m3, r.m6, r.y1, r.y2, r.y3, r.ytd, r.since, r.source AS ret_source,
              k.sharpe_1y, k.sharpe_2y, k.sharpe_3y, k.std_1y, k.std_2y, k.std_3y, k.as_of
       FROM funds f
       LEFT JOIN returns r ON r.code = f.code
       LEFT JOIN risk k ON k.code = f.code
       WHERE f.code = ?`
    ).bind(code).first();
    if (!item) return jsonEnvelope({ code: 404, data: null, message: "fund not found" }, 404);
    return jsonEnvelope({ code: 0, data: item });
  } catch (e) {
    return jsonEnvelope({ code: 500, data: null, message: e.message || "error" }, 500);
  }
}
