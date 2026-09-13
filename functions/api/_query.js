// !!! 本文件由 api/_query.js 同步而来, 请勿直接修改 (改源文件后: cp api/_query.js functions/api/_query.js)
// 纯查询构造模块: 不依赖任何 Node API, 三端共用 (Vercel / Netlify / Cloudflare Workers+D1)
// 查询参数 -> WHERE/ORDER BY (全部白名单, 无注入面)

export function buildQuery(q = {}) {
  const where = [];
  const args = [];
  const scope = q.scope === 'all' ? 'all' : 'bond';
  if (scope === 'bond') where.push('f.is_bond = 1');
  if (q.group && ['limited', 'unlimited', 'nodata'].includes(q.group)) {
    where.push('f.limit_group = ?');
    args.push(q.group);
  }
  if (q.status) {
    where.push('f.sgzt = ?');
    args.push(String(q.status).slice(0, 20));
  }
  if (q.type) {
    where.push('f.type LIKE ?');
    args.push(`%${String(q.type).slice(0, 30)}%`);
  }
  if (q.q) {
    const kw = `%${String(q.q).slice(0, 30).replace(/[%_]/g, '')}%`;
    where.push('(f.name LIKE ? OR f.code LIKE ?)');
    args.push(kw, kw);
  }
  const SORTS = {
    default: 'f.sort_order ASC, f.code ASC',
    limit_asc: '(f.daily_limit IS NULL) ASC, f.daily_limit ASC, f.code ASC',
    limit_desc: '(f.daily_limit IS NULL) DESC, f.daily_limit DESC, f.code ASC',
    y1_desc: "(CAST(NULLIF(r.y1,'') AS REAL) IS NULL) ASC, CAST(NULLIF(r.y1,'') AS REAL) DESC, f.code ASC",
    y1_asc: "(CAST(NULLIF(r.y1,'') AS REAL) IS NULL) ASC, CAST(NULLIF(r.y1,'') AS REAL) ASC, f.code ASC",
    sharpe_desc: "(CAST(NULLIF(k.sharpe_1y,'') AS REAL) IS NULL) ASC, CAST(NULLIF(k.sharpe_1y,'') AS REAL) DESC, f.code ASC",
  };
  const orderBy = SORTS[q.sort] || SORTS.default;
  return { where, args, orderBy, scope };
}

export const ITEM_SQL = `
SELECT
  f.code, f.name, f.type, f.sgzt, f.shzt, f.next_open_day,
  f.min_buy, f.daily_limit, f.limit_group, f.limit_display,
  f.fee_rate, f.nav, f.nav_date, f.is_bond,
  r.w, r.m1, r.m3, r.m6, r.y1, r.y2, r.y3, r.ytd, r.since, r.source AS ret_source,
  k.sharpe_1y, k.sharpe_2y, k.sharpe_3y, k.std_1y, k.std_2y, k.std_3y, k.as_of
FROM funds f
LEFT JOIN returns r ON r.code = f.code
LEFT JOIN risk k ON k.code = f.code
`;

export function jsonEnvelope(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": `public, max-age=300, s-maxage=300`,
    },
  });
}
