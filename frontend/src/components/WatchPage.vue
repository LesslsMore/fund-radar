<script setup>
import { computed, onMounted, ref } from "vue";
import { store, ensureWatchDetails, toggleWatch, watchSet, searchAll } from "../store.js";
import { getMeta } from "../api/client.js";
import { decorate } from "../logic.js";
import FundCard from "./FundCard.vue";
import Pager from "./Pager.vue";

const q = ref("");
const searching = ref(false);
const results = ref([]);

const watched = computed(() => [...watchSet()]);
const metaLine = computed(() => {
  const mt = store.meta;
  if (!mt) return "";
  return `数据日期 ${mt.data_date} · 爬取于 ${mt.built_at}`;
});

const decorated = computed(() =>
  store.watch.codes.map((c) => store.watch.details[c]).filter(Boolean).map(decorate)
);

const sorted = computed(() => {
  const num = (v) => {
    const n = parseFloat(v);
    return Number.isNaN(n) ? null : n;
  };
  const sorters = {
    limit_asc: (a, b) => (a.daily_limit ?? 1e15) - (b.daily_limit ?? 1e15),
    y1_desc: (a, b) => (num(b.y1) ?? -1e9) - (num(a.y1) ?? -1e9),
    sharpe_desc: (a, b) => (num(b.sharpe_1y) ?? -1e9) - (num(a.sharpe_1y) ?? -1e9),
  };
  return [...decorated.value].sort(sorters[store.watch.sort] || sorters.limit_asc);
});

const pageCount = computed(() => Math.max(1, Math.ceil(sorted.value.length / store.watch.pageSize)));
const paged = computed(() =>
  sorted.value.slice((store.watch.page - 1) * store.watch.pageSize, store.watch.page * store.watch.pageSize)
);

async function doSearch() {
  const kw = q.value.trim();
  if (!kw) return;
  searching.value = true;
  try {
    results.value = await searchAll(kw);
  } catch {
    results.value = [];
  }
  searching.value = false;
}

onMounted(async () => {
  ensureWatchDetails();
  if (!store.meta) {
    try {
      store.meta = await getMeta();
    } catch {}
  }
});
</script>

<template>
  <div class="header">
    <div class="row1">
      <h1>⭐ 我的自选</h1>
      <span class="date">{{ metaLine }}</span>
    </div>
    <div class="counts"><span><b>{{ store.watch.codes.length }}</b> 已自选</span></div>
  </div>

  <div class="filters">
    <div class="addrow">
      <input class="search addin" v-model="q" type="search" inputmode="search"
             placeholder="输入代码或名称，从全部 27526 只中添加…" @keyup.enter="doSearch" />
      <button class="addbtn" @click="doSearch">{{ searching ? "搜索中…" : "搜索" }}</button>
    </div>
    <div class="addresults" v-if="results.length">
      <div class="addrow-item" v-for="r in results" :key="r.code">
        <span class="ar-name">{{ r.name }} <text class="ar-code">{{ r.code }}</text></span>
        <button class="ar-add" :disabled="watched.includes(r.code)"
                @click="toggleWatch(r.code); ensureWatchDetails()">
          {{ watched.includes(r.code) ? "已自选" : "+ 自选" }}
        </button>
      </div>
    </div>

    <div class="sortrow">
      <span class="slabel">排序</span>
      <select v-model="store.watch.sort" style="flex:1">
        <option value="limit_asc">限额 ↑</option>
        <option value="y1_desc">近1年收益 ↓</option>
        <option value="sharpe_desc">近1年夏普 ↓</option>
      </select>
    </div>
  </div>

  <div class="list" v-if="!store.watch.loading">
    <FundCard v-for="f in paged" :key="f.code" :f="f" :watched="true"
              @toggle-watch="toggleWatch(f.code); ensureWatchDetails()" />
    <div class="empty" v-if="!sorted.length">
      还没有自选基金。去「债基」或「QDII」页点卡片右上角的 ☆ 收藏，或用上方搜索添加。
    </div>
    <Pager :page="store.watch.page" :page-count="pageCount"
           @go="store.watch.page = Math.min(Math.max(1, $event), pageCount)" />
    <div class="foot">显示 {{ paged.length }} / {{ sorted.length }} 只 · 点击卡片展开详情 · ★ 取消自选</div>
  </div>
  <div class="skeleton" v-if="store.watch.loading">加载自选数据中…</div>
</template>
