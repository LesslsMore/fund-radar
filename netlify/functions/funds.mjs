// Netlify Functions v2: GET /api/funds —— 与 Vercel 版共用 api/_lib.js 查询层
import { runQuery } from '../../api/_lib.js';

export const config = { path: "/api/funds" };

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
    const url = new URL(req.url);
    const q = Object.fromEntries(url.searchParams.entries());
    const data = await runQuery(q);
    return json({ code: 0, data, message: "ok" });
  } catch (e) {
    return json({ code: 400, data: null, message: e.message || "bad request" }, 400);
  }
};
