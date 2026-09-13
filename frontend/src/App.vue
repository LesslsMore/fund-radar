<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { getMeta, getFunds } from './api/client.js';
import FundCard from './components/FundCard.vue';

const loading = ref(true);
const error = ref('');
const meta = ref(null);
const funds = ref([]);

const GROUPS = [
  { key: 'limited', label: '有限额' },
  { key: 'unlimited', label: '无限额' },
  { key: 'nodata', label: '无数据' },
  { key: 'all', label: '全部' },
];
const STATUSES = ['开放申购', '限大额', '暂停申购', '封闭期', '认购期'];

// 可排序字段 (Excel 式多级排序的候选键)
const SORT_FIELDS = [
  { key: 'default', label: '默认顺序', get: null },
  { key: 'limit', label: '日累计限额', get: (f) => f.daily_limit },
  { key: 'y1', label: '近1年收益', get: (f) => parseFloat(f.y1) },
  { key: 'y2', label: '近2年收益', get: (f) => parseFloat(f.y2) },
  { key: 'y3', label: '近3年收益', get: (f) => parseFloat(f.y3) },
  { key: 'sharpe1', label: '近1年夏普', get: (f) => parseFloat(f.sharpe_1y) },
  { key: 'sharpe2', label: '近2年夏普', get: (f) => parseFloat(f.sharpe_2y) },
  { key: 'sharpe3', label: '近3年夏普', get: (f) => parseFloat(f.sharpe_3y) },
];

// 条件筛选可用的指标
const METRICS = [
  { key: 'limit', label: '日累计限额', unit: '元', get: (f) => f.daily_limit },
  { key: 'w', label: '近1周收益', unit: '%', get: (f) => parseFloat(f.w) },
  { key: 'm1', label: '近1月收益', unit: '%', get: (f) => parseFloat(f.m1) },
  { key: 'm3', label: '近3月收益', unit: '%', get: (f) => parseFloat(f.m3) },
  { key: 'm6', label: '近6月收益', unit: '%', get: (f) => parseFloat(f.m6) },
  { key: 'y1', label: '近1年收益', unit: '%', get: (f) => parseFloat(f.y1) },
  { key: 'y2', label: '近2年收益', unit: '%', get: (f) => parseFloat(f.y2) },
  { key: 'y3', label: '近3年收益', unit: '%', get: (f) => parseFloat(f.y3) },
  { key: 'ytd', label: '今年来收益', unit: '%', get: (f) => parseFloat(f.ytd) },
  { key: 'since', label: '成立来收益', unit: '%', get: (f) => parseFloat(f.since) },
  { key: 'sharpe1', label: '近1年夏普', unit: '', get: (f) => parseFloat(f.sharpe_1y) },
  { key: 'sharpe2', label: '近2年夏普', unit: '', get: (f) => parseFloat(f.sharpe_2y) },
  { key: 'sharpe3', label: '近3年夏普', unit: '', get: (f) => parseFloat(f.sharpe_3y) },
];
const METRIC_MAP = new Map(METRICS.map((m) => [m.key, m]));
const unitOf = (key) => METRIC_MAP.get(key)?.unit || '';

const group = ref('limited');
const status = ref('');
const typeSel = ref([]);            // 类型多选 (空 = 全部)
const typePanelOpen = ref(false);
const conditions = ref([]);         // 条件筛选 [{metric, op, value}]
const condPanelOpen = ref(false);
const condMode = ref('any');        // any=满足任一(或) all=全部满足(与)
const primary = ref('limit');       // 第一排序
const primaryAsc = ref(true);
const secondary = ref('y1');        // 第二排序
const secondaryAsc = ref(false);
const keyword = ref('');
const PAGE = 50;
const visibleCount = ref(PAGE);
const sentinel = ref(null);
let observer = null;

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [m, r] = await Promise.all([getMeta(), getFunds({ scope: 'bond', all: '1' })]);
    meta.value = m;
    funds.value = r.items;
  } catch (e) {
    error.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}
load();

const groupCount = computed(() => {
  const c = { limited: 0, unlimited: 0, nodata: 0, all: funds.value.length };
  for (const f of funds.value) c[f.limit_group]++;
  return c;
});

const types = computed(() => {
  const s = new Set();
  for (const f of funds.value) s.add(f.type);
  return [...s].filter(Boolean).sort();
});
const typeLabel = computed(() =>
  typeSel.value.length ? `类型(${typeSel.value.length})` : '类型: 全部'
);

// 完整可用的条件 (指标已选且数值已填)
const activeConds = computed(() =>
  conditions.value.filter((c) => c.metric && c.value !== '' && !Number.isNaN(parseFloat(c.value)))
);
const condLabel = computed(() =>
  activeConds.value.length ? `条件(${activeConds.value.length})` : '条件'
);

function checkCond(f, c) {
  const def = METRIC_MAP.get(c.metric);
  const v = def ? def.get(f) : null;
  if (v == null || Number.isNaN(v)) return false; // 缺数据视为不满足
  const t = parseFloat(c.value);
  if (c.op === '>') return v > t;
  if (c.op === '≥') return v >= t;
  if (c.op === '<') return v < t;
  if (c.op === '≤') return v <= t;
  return false;
}

const filtered = computed(() => {
  let list = funds.value;
  if (group.value !== 'all') list = list.filter((f) => f.limit_group === group.value);
  if (status.value) list = list.filter((f) => f.sgzt === status.value);
  if (typeSel.value.length) list = list.filter((f) => typeSel.value.includes(f.type));
  const kw = keyword.value.trim().toLowerCase();
  if (kw) list = list.filter((f) => f.name.toLowerCase().includes(kw) || f.code.includes(kw));
  const conds = activeConds.value;
  if (conds.length) {
    list = list.filter((f) =>
      condMode.value === 'any'
        ? conds.some((c) => checkCond(f, c))
        : conds.every((c) => checkCond(f, c))
    );
  }

  const pf = SORT_FIELDS.find((s) => s.key === primary.value);
  const sf = SORT_FIELDS.find((s) => s.key === secondary.value);
  const idxMap = new Map(list.map((f, i) => [f, i]));
  const val = (f, def) => {
    if (!def.get) return idxMap.get(f); // 默认顺序 = 原始分组序
    const v = def.get(f);
    return v == null || Number.isNaN(v) ? null : v;
  };
  return [...list].sort((a, b) => {
    for (const [def, asc] of [[pf, primaryAsc.value], [sf, secondaryAsc.value]]) {
      const va = val(a, def);
      const vb = val(b, def);
      if (va === null && vb === null) continue;
      if (va === null) return 1;   // 缺值永远排最后
      if (vb === null) return -1;
      if (va !== vb) return asc ? va - vb : vb - va;
    }
    return a.code.localeCompare(b.code);
  });
});

const visible = computed(() => filtered.value.slice(0, visibleCount.value));

watch([group, status, typeSel, primary, primaryAsc, secondary, secondaryAsc, keyword, conditions, condMode],
  () => { visibleCount.value = PAGE; }, { deep: true });

function setupObserver() {
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && visibleCount.value < filtered.value.length) {
      visibleCount.value += PAGE;
    }
  }, { rootMargin: '300px' });
  observer.observe(sentinel.value);
}
onMounted(setupObserver);

function addCond() {
  conditions.value.push({ metric: 'y1', op: '>', value: '' });
}

const metaLine = computed(() => {
  const m = meta.value;
  if (!m) return '';
  return `数据日期 ${m.data_date} · 爬取于 ${m.built_at}`;
});
</script>

<template>
  <div class="header">
    <div class="row1">
      <h1>📊 基金雷达</h1>
      <span class="date">{{ metaLine }}</span>
    </div>
    <div class="counts" v-if="meta">
      <span><b>{{ meta.limited_total }}</b>有限额</span>
      <span><b>{{ meta.unlimited_total }}</b>无限额</span>
      <span><b>{{ meta.nodata_total }}</b>无数据</span>
      <span><b>{{ meta.bond_total }}</b>债券型</span>
    </div>
  </div>

  <div class="filters">
    <input v-model="keyword" class="search" type="search" inputmode="search" placeholder="搜索基金代码 / 名称…" />
    <div class="tabs">
      <button v-for="g in GROUPS" :key="g.key" class="tab" :class="{ on: group === g.key }" @click="group = g.key">
        {{ g.label }}<span class="n" v-if="funds.length">{{ groupCount[g.key] }}</span>
      </button>
    </div>
    <div class="selects">
      <select v-model="status">
        <option value="">申购状态：全部</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
      </select>
      <button class="type-btn" :class="{ on: typeSel.length }" @click="typePanelOpen = !typePanelOpen">
        {{ typeLabel }}
      </button>
      <button class="type-btn" :class="{ on: activeConds.length }" @click="condPanelOpen = !condPanelOpen">
        {{ condLabel }}
      </button>
    </div>
    <div class="sortrows">
      <div class="sortrow">
        <span class="slabel">第一</span>
        <select v-model="primary">
          <option v-for="s in SORT_FIELDS" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
        <button class="dirbtn" @click="primaryAsc = !primaryAsc">{{ primaryAsc ? '↑' : '↓' }}</button>
      </div>
      <div class="sortrow">
        <span class="slabel">第二</span>
        <select v-model="secondary">
          <option v-for="s in SORT_FIELDS" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
        <button class="dirbtn" @click="secondaryAsc = !secondaryAsc">{{ secondaryAsc ? '↑' : '↓' }}</button>
      </div>
    </div>

    <!-- 类型多选面板 -->
    <div v-if="typePanelOpen" class="type-backdrop" @click="typePanelOpen = false"></div>
    <div v-if="typePanelOpen" class="type-panel">
      <div class="tp-head"><b>基金类型（可多选，如 中短债 + 长债）</b><button @click="typePanelOpen = false">完成</button></div>
      <label class="tp-item" v-for="t in types" :key="t">
        <input type="checkbox" :value="t" v-model="typeSel" /> {{ t }}
      </label>
      <button class="tp-clear" v-if="typeSel.length" @click="typeSel = []">清空已选 ({{ typeSel.length }})</button>
    </div>

    <!-- 条件筛选面板 -->
    <div v-if="condPanelOpen" class="type-backdrop" @click="condPanelOpen = false"></div>
    <div v-if="condPanelOpen" class="type-panel">
      <div class="tp-head"><b>条件筛选（例：近1年收益 &gt; 3%）</b><button @click="condPanelOpen = false">完成</button></div>
      <div class="cond-mode">
        条件间关系：
        <label><input type="radio" value="any" v-model="condMode" />满足任一(或)</label>
        <label><input type="radio" value="all" v-model="condMode" />全部满足(与)</label>
      </div>
      <div class="cond-row" v-for="(c, i) in conditions" :key="i">
        <select v-model="c.metric">
          <option v-for="m in METRICS" :key="m.key" :value="m.key">{{ m.label }}</option>
        </select>
        <select v-model="c.op" class="op">
          <option>&gt;</option>
          <option>≥</option>
          <option>&lt;</option>
          <option>≤</option>
        </select>
        <input type="number" step="any" inputmode="decimal" v-model="c.value" placeholder="数值" />
        <span class="unit">{{ unitOf(c.metric) }}</span>
        <button class="del" @click="conditions.splice(i, 1)">×</button>
      </div>
      <div v-if="!conditions.length" class="cond-empty">还没有条件，点下面添加一条</div>
      <button class="addcond" @click="addCond">+ 添加条件</button>
      <div class="cond-hint">提示：缺数据视为不满足该条件（如成立不满两年的基金没有"近2年收益"）。多个条件用上方关系组合，如 [近1年收益 &gt; 3%] 或 [近2年收益 &gt; 2.5%]。</div>
    </div>
  </div>

  <div class="list" v-if="!loading && !error">
    <FundCard v-for="f in visible" :key="f.code" :f="f" />
    <div v-if="!filtered.length" class="empty">没有符合条件的基金 🤷</div>
    <div ref="sentinel" style="height: 1px"></div>
    <div class="foot">
      显示 {{ visible.length }} / {{ filtered.length }} 只 · 点击卡片展开详情 · 数据源：天天基金
    </div>
  </div>
  <div v-if="loading" class="skeleton">加载中…（首次加载后支持离线）</div>
  <div v-if="error" class="err">
    加载失败：{{ error }}
    <div><button @click="load">重试</button></div>
  </div>
</template>
