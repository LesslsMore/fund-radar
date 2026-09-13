<script setup>
import { computed, onMounted } from "vue";
import { store, ensureLoaded, toggleWatch, watchSet } from "../store.js";
import { GROUPS, STATUSES, SORT_FIELDS, METRICS, unitOf, applyFilters, decorate } from "../logic.js";
import FundCard from "./FundCard.vue";
import Pager from "./Pager.vue";

const props = defineProps({ module: { type: String, required: true } }); // bond | qdii

const m = computed(() => store.modules[props.module]);
const isBond = computed(() => props.module === "bond");
const title = computed(() => (isBond.value ? "📊 债基雷达" : "🌍 QDII 基金"));

const types = computed(() => {
  const s = new Set();
  for (const f of m.value.funds) s.add(f.type);
  return [...s].filter(Boolean).sort();
});

const groupCount = computed(() => {
  const c = { limited: 0, unlimited: 0, nodata: 0, all: m.value.funds.length };
  for (const f of m.value.funds) c[f.limit_group]++;
  return c;
});

const filtered = computed(() =>
  applyFilters(m.value.funds, {
    group: m.value.group,
    status: m.value.status,
    typeSel: m.value.typeSel,
    keyword: m.value.keyword,
    conds: m.value.conditions,
    condMode: m.value.condMode,
    primary: m.value.primary,
    primaryAsc: m.value.primaryAsc,
    secondary: m.value.secondary,
    secondaryAsc: m.value.secondaryAsc,
  })
);

const pageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / m.value.pageSize)));
const paged = computed(() =>
  filtered.value
    .slice((m.value.page - 1) * m.value.pageSize, m.value.page * m.value.pageSize)
    .map(decorate)
);

const watchCodes = computed(() => [...watchSet()]);

const metaLine = computed(() => {
  const mt = store.meta;
  if (!mt) return "";
  return `数据日期 ${mt.data_date} · 爬取于 ${mt.built_at}`;
});

function goPage(p) {
  m.value.page = Math.min(Math.max(1, p), pageCount.value);
}

onMounted(() => ensureLoaded(props.module));
</script>

<template>
  <div class="header">
    <div class="row1">
      <h1>{{ title }}</h1>
      <span class="date">{{ metaLine }}</span>
    </div>
    <div class="counts" v-if="m.loaded">
      <span><b>{{ groupCount.limited }}</b> 有限额</span>
      <span><b>{{ groupCount.unlimited }}</b> 无限额</span>
      <span><b>{{ groupCount.nodata }}</b> 无数据</span>
      <span><b>{{ groupCount.all }}</b> 总数</span>
    </div>
  </div>

  <div class="filters">
    <input class="search" v-model="m.keyword" type="search" inputmode="search"
           placeholder="搜索基金代码 / 名称…" @input="m.page = 1" />

    <div class="tabs">
      <button v-for="g in GROUPS" :key="g.key" class="tab"
              :class="{ on: m.group === g.key }" @click="m.group = g.key; m.page = 1">
        {{ g.label }}<span class="n" v-if="m.funds.length"> {{ groupCount[g.key] }}</span>
      </button>
    </div>

    <div class="selects">
      <select v-model="m.status" @change="m.page = 1">
        <option value="">申购状态：全部</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
      </select>
      <button class="type-btn" :class="{ on: m.typeSel.length }"
              @click="m.typePanelOpen = !m.typePanelOpen; m.condPanelOpen = false">
        类型{{ m.typeSel.length ? "(" + m.typeSel.length + ")" : ": 全部" }}
      </button>
      <button class="type-btn" :class="{ on: m.conditions.length }"
              @click="m.condPanelOpen = !m.condPanelOpen; m.typePanelOpen = false">
        条件{{ m.conditions.length ? "(" + m.conditions.length + ")" : "" }}
      </button>
    </div>

    <div class="sortrows">
      <div class="sortrow">
        <span class="slabel">第一</span>
        <select v-model="m.primary" @change="m.page = 1">
          <option v-for="s in SORT_FIELDS" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
        <button class="dirbtn" @click="m.primaryAsc = !m.primaryAsc; m.page = 1">{{ m.primaryAsc ? "↑" : "↓" }}</button>
      </div>
      <div class="sortrow">
        <span class="slabel">第二</span>
        <select v-model="m.secondary" @change="m.page = 1">
          <option v-for="s in SORT_FIELDS" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
        <button class="dirbtn" @click="m.secondaryAsc = !m.secondaryAsc; m.page = 1">{{ m.secondaryAsc ? "↑" : "↓" }}</button>
      </div>
    </div>

    <div class="mask" v-if="m.typePanelOpen || m.condPanelOpen" @click="m.typePanelOpen = m.condPanelOpen = false"></div>

    <div class="panel" v-if="m.typePanelOpen">
      <div class="phead"><b>基金类型（可多选，如 中短债 + 长债）</b>
        <button class="pdone" @click="m.typePanelOpen = false">完成</button></div>
      <label class="pitem" v-for="t in types" :key="t">
        <input type="checkbox" :value="t" v-model="m.typeSel" @change="m.page = 1" /> {{ t }}
      </label>
      <button class="pclear" v-if="m.typeSel.length" @click="m.typeSel = []; m.page = 1">
        清空已选 ({{ m.typeSel.length }})
      </button>
    </div>

    <div class="panel" v-if="m.condPanelOpen">
      <div class="phead"><b>条件筛选（例：近1年收益 &gt; 3%）</b>
        <button class="pdone" @click="m.condPanelOpen = false">完成</button></div>
      <div class="cond-mode">
        条件间关系：
        <label><input type="radio" value="any" v-model="m.condMode" @change="m.page = 1" />满足任一(或)</label>
        <label><input type="radio" value="all" v-model="m.condMode" @change="m.page = 1" />全部满足(与)</label>
      </div>
      <div class="cond-row" v-for="(c, i) in m.conditions" :key="i">
        <select v-model="c.metric" @change="m.page = 1">
          <option v-for="mt in METRICS" :key="mt.key" :value="mt.key">{{ mt.label }}</option>
        </select>
        <select v-model="c.op" class="op" @change="m.page = 1">
          <option>&gt;</option><option>≥</option><option>&lt;</option><option>≤</option>
        </select>
        <input type="number" step="any" inputmode="decimal" v-model="c.value"
               placeholder="数值" @input="m.page = 1" />
        <span class="cunit">{{ unitOf(c.metric) }}</span>
        <button class="cdel" @click="m.conditions.splice(i, 1); m.page = 1">×</button>
      </div>
      <div class="cond-empty" v-if="!m.conditions.length">还没有条件，点下面添加一条</div>
      <button class="paddcond" @click="m.conditions.push({ metric: 'y1', op: '>', value: '' }); m.page = 1">
        + 添加条件
      </button>
      <div class="chint">缺数据视为不满足该条件。多个条件可用上方关系组合，如 [近1年收益 &gt; 3%] 或 [近2年收益 &gt; 2.5%]。</div>
    </div>
  </div>

  <div class="list" v-if="!m.loading && !m.error">
    <FundCard v-for="f in paged" :key="f.code" :f="f"
              :watched="watchCodes.includes(f.code)" @toggle-watch="toggleWatch(f.code)" />
    <div class="empty" v-if="!filtered.length">没有符合条件的基金 🤷</div>
    <Pager :page="m.page" :page-count="pageCount" @go="goPage" />
    <div class="pgsize">
      每页
      <select v-model.number="m.pageSize" @change="m.page = 1">
        <option :value="50">50</option>
        <option :value="100">100</option>
        <option :value="200">200</option>
      </select>
      条 · 共 {{ filtered.length }} 只 · 数据源：天天基金
    </div>
  </div>
  <div class="skeleton" v-if="m.loading">加载中…</div>
  <div class="err" v-if="m.error">
    加载失败：{{ m.error }}
    <div><button class="retrybtn" @click="ensureLoaded(module)">重试</button></div>
  </div>
</template>
