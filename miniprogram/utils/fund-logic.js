// 基金雷达 - 平台无关的业务逻辑模块 (CommonJS)
// 与 PWA (frontend/src/App.vue) 的筛选/排序/条件逻辑保持一致
// 该模块不依赖任何小程序/浏览器 API, 可被任意端复用

const GROUPS = [
  { key: "limited", label: "有限额" },
  { key: "unlimited", label: "无限额" },
  { key: "nodata", label: "无数据" },
  { key: "all", label: "全部" },
];

const STATUSES = ["开放申购", "限大额", "暂停申购", "封闭期", "认购期"];

// 可排序字段
const SORT_FIELDS = [
  { key: "default", label: "默认顺序", get: null },
  { key: "limit", label: "日累计限额", get: (f) => f.daily_limit },
  { key: "y1", label: "近1年收益", get: (f) => toNum(f.y1) },
  { key: "y2", label: "近2年收益", get: (f) => toNum(f.y2) },
  { key: "y3", label: "近3年收益", get: (f) => toNum(f.y3) },
  { key: "sharpe1", label: "近1年夏普", get: (f) => toNum(f.sharpe_1y) },
  { key: "sharpe2", label: "近2年夏普", get: (f) => toNum(f.sharpe_2y) },
  { key: "sharpe3", label: "近3年夏普", get: (f) => toNum(f.sharpe_3y) },
];

// 条件筛选可用的指标
const METRICS = [
  { key: "limit", label: "日累计限额", unit: "元", get: (f) => f.daily_limit },
  { key: "w", label: "近1周收益", unit: "%", get: (f) => toNum(f.w) },
  { key: "m1", label: "近1月收益", unit: "%", get: (f) => toNum(f.m1) },
  { key: "m3", label: "近3月收益", unit: "%", get: (f) => toNum(f.m3) },
  { key: "m6", label: "近6月收益", unit: "%", get: (f) => toNum(f.m6) },
  { key: "y1", label: "近1年收益", unit: "%", get: (f) => toNum(f.y1) },
  { key: "y2", label: "近2年收益", unit: "%", get: (f) => toNum(f.y2) },
  { key: "y3", label: "近3年收益", unit: "%", get: (f) => toNum(f.y3) },
  { key: "ytd", label: "今年来收益", unit: "%", get: (f) => toNum(f.ytd) },
  { key: "since", label: "成立来收益", unit: "%", get: (f) => toNum(f.since) },
  { key: "sharpe1", label: "近1年夏普", unit: "", get: (f) => toNum(f.sharpe_1y) },
  { key: "sharpe2", label: "近2年夏普", unit: "", get: (f) => toNum(f.sharpe_2y) },
  { key: "sharpe3", label: "近3年夏普", unit: "", get: (f) => toNum(f.sharpe_3y) },
];

const METRIC_MAP = {};
METRICS.forEach((m) => (METRIC_MAP[m.key] = m));

function toNum(v) {
  if (v === "" || v == null) return null;
  const n = parseFloat(v);
  return Number.isNaN(n) ? null : n;
}

function pctText(v) {
  const n = toNum(v);
  if (n === null) return { text: "--", cls: "muted" };
  return { text: (n > 0 ? "+" : "") + n.toFixed(2) + "%", cls: n > 0 ? "pos" : n < 0 ? "neg" : "muted" };
}

function unitOf(key) {
  return (METRIC_MAP[key] && METRIC_MAP[key].unit) || "";
}

// 单条条件判断 (缺数据视为不满足)
function checkCond(f, c) {
  const def = METRIC_MAP[c.metric];
  const v = def ? def.get(f) : null;
  if (v === null) return false;
  const t = parseFloat(c.value);
  if (Number.isNaN(t)) return true; // 数值未填的条件视为恒真 (调用方应过滤掉不完整条件)
  if (c.op === ">") return v > t;
  if (c.op === "≥") return v >= t;
  if (c.op === "<") return v < t;
  if (c.op === "≤") return v <= t;
  return false;
}

// 筛选 + 多级排序
// opt: { group, status, typeSel, keyword, conds, condMode, primary, primaryAsc, secondary, secondaryAsc }
function applyFilters(funds, opt) {
  let list = funds;
  if (opt.group && opt.group !== "all") list = list.filter((f) => f.limit_group === opt.group);
  if (opt.status) list = list.filter((f) => f.sgzt === opt.status);
  if (opt.typeSel && opt.typeSel.length) list = list.filter((f) => opt.typeSel.indexOf(f.type) >= 0);
  const kw = (opt.keyword || "").trim().toLowerCase();
  if (kw) list = list.filter((f) => f.name.toLowerCase().indexOf(kw) >= 0 || f.code.indexOf(kw) >= 0);

  const conds = (opt.conds || []).filter(
    (c) => c.metric && c.value !== "" && !Number.isNaN(parseFloat(c.value))
  );
  if (conds.length) {
    list = list.filter((f) =>
      opt.condMode === "all"
        ? conds.every((c) => checkCond(f, c))
        : conds.some((c) => checkCond(f, c))
    );
  }

  const pf = SORT_FIELDS.filter((s) => s.key === opt.primary)[0] || SORT_FIELDS[0];
  const sf = SORT_FIELDS.filter((s) => s.key === opt.secondary)[0] || SORT_FIELDS[1];
  const idxMap = {};
  list.forEach((f, i) => (idxMap[f.code] = i));
  const val = (f, def) => (def.get ? def.get(f) : idxMap[f.code]);
  const sorted = list.slice().sort((a, b) => {
    const pair = [
      [pf, opt.primaryAsc],
      [sf, opt.secondaryAsc],
    ];
    for (let k = 0; k < 2; k++) {
      const va = val(a, pair[k][0]);
      const vb = val(b, pair[k][0]);
      if (va === null && vb === null) continue;
      if (va === null) return 1;
      if (vb === null) return -1;
      if (va !== vb) return pair[k][1] ? va - vb : vb - va;
    }
    return a.code < b.code ? -1 : a.code > b.code ? 1 : 0;
  });
  return sorted;
}

// 预计算卡片展示字段 (WXML 无法调用函数, 全部在 JS 侧算好)
function decorate(f) {
  const y1 = pctText(f.y1), y2 = pctText(f.y2), y3 = pctText(f.y3);
  const num2 = (v) => {
    const n = toNum(v);
    return n === null ? "--" : n.toFixed(2);
  };
  const sgztCls =
    f.sgzt === "开放申购" ? "badge open" :
    f.sgzt === "限大额" ? "badge big" :
    f.sgzt === "暂停申购" ? "badge pause" :
    (f.sgzt === "封闭期" || f.sgzt === "认购期") ? "badge close" : "badge";
  const cells = [
    ["近1周", f.w], ["近1月", f.m1], ["近3月", f.m3],
    ["近6月", f.m6], ["近1年", f.y1], ["近2年", f.y2],
    ["近3年", f.y3], ["今年来", f.ytd], ["成立来", f.since],
  ].map(function (p) {
    const t = pctText(p[1]);
    return { k: p[0], text: t.text, cls: t.cls };
  });
  const nav = toNum(f.nav);
  return Object.assign({}, f, {
    sgztCls: sgztCls,
    y1Text: y1.text, y1Cls: y1.cls,
    y2Text: y2.text, y2Cls: y2.cls,
    y3Text: y3.text, y3Cls: y3.cls,
    s1Text: num2(f.sharpe_1y), s2Text: num2(f.sharpe_2y), s3Text: num2(f.sharpe_3y),
    std1: f.std_1y || "--",
    navText: nav === null ? "--" : nav.toFixed(4),
    feeText: f.fee_rate || "--",
    minBuyText: f.min_buy == null ? "--" : f.min_buy + "元",
    detailCells: cells,
  });
}

module.exports = {
  GROUPS: GROUPS,
  STATUSES: STATUSES,
  SORT_FIELDS: SORT_FIELDS,
  METRICS: METRICS,
  unitOf: unitOf,
  applyFilters: applyFilters,
  decorate: decorate,
  checkCond: checkCond,
};
