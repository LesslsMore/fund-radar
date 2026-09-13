// Pages Functions: GET /api/funds?scope=&group=&status=&type=&q=&sort=&page=&page_size=|all=1
import { runQuery } from './_d1.js';
import { jsonEnvelope } from './_query.js';

export async function onRequestGet({ request, env }) {
  try {
    const q = Object.fromEntries(new URL(request.url).searchParams.entries());
    return jsonEnvelope({ code: 0, data: await runQuery(env.DB, q), message: "ok" });
  } catch (e) {
    return jsonEnvelope({ code: 400, data: null, message: e.message || "bad request" }, 400);
  }
}
