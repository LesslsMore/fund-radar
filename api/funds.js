import { ok, fail, runQuery } from './_lib.js';

// GET /api/funds?scope=bond|all&group=limited|unlimited|nodata&status=限大额&type=长债
//              &q=搜索词&sort=default|limit_asc|limit_desc|y1_desc|y1_asc|sharpe_desc
//              &page=1&page_size=50 | all=1
export default async function handler(req, res) {
  try {
    const url = new URL(req.url, 'http://x');
    const q = Object.fromEntries(url.searchParams.entries());
    const data = runQuery(q);
    ok(res, data, 300);
  } catch (e) {
    fail(res, 400, e.message || 'bad request');
  }
}
