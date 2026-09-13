// 全局状态: 分模块的列表状态 + 自选 (localStorage 持久化)
import { reactive } from "vue";
import { getMeta, getFunds, getFund } from "./api/client.js";

const WATCH_KEY = "fund-radar-watch-v1";

function loadWatch() {
  try {
    const v = JSON.parse(localStorage.getItem(WATCH_KEY));
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

function defaultModuleState() {
  return {
    loaded: false,
    loading: false,
    error: "",
    funds: [],
    group: "limited",
    status: "",
    typeSel: [],
    typePanelOpen: false,
    condPanelOpen: false,
    conditions: [],
    condMode: "any",
    primary: "limit",
    primaryAsc: true,
    secondary: "y1",
    secondaryAsc: false,
    keyword: "",
    page: 1,
    pageSize: 50,
  };
}

export const store = reactive({
  meta: null,
  tab: "bond",
  modules: {
    bond: defaultModuleState(),
    qdii: defaultModuleState(),
  },
  watch: {
    codes: loadWatch(),
    details: {},       // code -> 完整记录
    loading: false,
    error: "",
    page: 1,
    pageSize: 50,
    sort: "limit_asc",
  },
});

export function watchSet() {
  return new Set(store.watch.codes);
}

export function toggleWatch(code) {
  const i = store.watch.codes.indexOf(code);
  if (i >= 0) store.watch.codes.splice(i, 1);
  else store.watch.codes.push(code);
  try {
    localStorage.setItem(WATCH_KEY, JSON.stringify(store.watch.codes));
  } catch {}
}

export async function ensureLoaded(moduleKey) {
  const m = store.modules[moduleKey];
  if (m.loaded || m.loading) return;
  m.loading = true;
  try {
    const params =
      moduleKey === "bond"
        ? { scope: "bond", all: "1" }
        : { scope: "all", type: "QDII", all: "1" };
    const [meta, r] = await Promise.all([
      store.meta ? Promise.resolve(store.meta) : getMeta(),
      getFunds(params),
    ]);
    store.meta = meta;
    m.funds = r.items;
    m.loaded = true;
  } catch (e) {
    m.error = String(e.message || e);
  } finally {
    m.loading = false;
  }
}

export async function ensureWatchDetails() {
  const w = store.watch;
  const missing = w.codes.filter((c) => !w.details[c]);
  if (!missing.length) return;
  w.loading = true;
  w.error = "";
  try {
    const results = await Promise.allSettled(missing.map((c) => getFund(c)));
    missing.forEach((c, i) => {
      if (results[i].status === "fulfilled" && results[i].value && results[i].value.code) {
        w.details[c] = results[i].value;
      } else {
        w.details[c] = { code: c, name: c + "（数据不可用）", limit_group: "nodata", limit_display: "--" };
      }
    });
    for (const c of Object.keys(w.details)) {
      if (!w.codes.includes(c)) delete w.details[c];
    }
  } finally {
    w.loading = false;
  }
}

export async function searchAll(q) {
  const r = await getFunds({ scope: "all", q, page_size: 10 });
  return r.items;
}
