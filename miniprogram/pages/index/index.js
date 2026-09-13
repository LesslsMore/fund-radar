const api = require("../../utils/api.js");
const L = require("../../utils/fund-logic.js");

const PAGE_SIZE = 50;

Page({
  data: {
    loading: true,
    errorMsg: "",

    metaLine: "",
    counts: { limited: 0, unlimited: 0, nodata: 0, all: 0 },

    group: "limited",
    statusIndex: 0,           // 0 = 全部
    typeSel: [],              // 选中的类型名数组
    typeItems: [],            // [{name, checked}] 供 checkbox 渲染
    typePanelOpen: false,
    condPanelOpen: false,
    conditions: [],           // [{metric, metricLabel, op, value}]
    condMode: "any",
    primaryIdx: 1,            // 默认 日累计限额
    primaryAsc: true,
    secondaryIdx: 2,          // 默认 近1年收益
    secondaryAsc: false,
    keyword: "",

    groups: L.GROUPS,
    statOptions: ["全部"].concat(L.STATUSES),
    sortLabels: L.SORT_FIELDS.map(function (s) { return s.label; }),
    metricLabels: L.METRICS.map(function (m) { return m.label; }),
    ops: [">", "≥", "<", "≤"],

    list: [],
    filteredCount: 0,
    visibleCount: PAGE_SIZE,
    expanded: {},

    lastUpdated: "",
  },

  allFunds: [],

  onLoad: function () {
    this.load();
  },

  load: function () {
    const that = this;
    this.setData({ loading: true, errorMsg: "" });
    Promise.all([api.getMeta(), api.getFunds({ scope: "bond", all: "1" })])
      .then(function (rs) {
        const meta = rs[0];
        const funds = rs[1].items;
        that.allFunds = funds;
        const typeSet = {};
        funds.forEach(function (f) { typeSet[f.type] = true; });
        that.setData({
          loading: false,
          meta: meta,
          lastUpdated: "数据日期 " + meta.data_date + " · 爬取于 " + meta.built_at,
          typeItems: Object.keys(typeSet).sort().map(function (t) {
            return { name: t, checked: that.data.typeSel.indexOf(t) >= 0 };
          }),
        });
        that.apply();
      })
      .catch(function (e) {
        that.setData({ loading: false, errorMsg: String(e.message || e) });
      });
  },

  refreshCounts: function () {
    const c = { limited: 0, unlimited: 0, nodata: 0, all: this.allFunds.length };
    this.allFunds.forEach(function (f) { c[f.limit_group]++; });
    this.setData({ counts: c });
  },

  apply: function () {
    const d = this.data;
    const out = L.applyFilters(this.allFunds, {
      group: d.group,
      status: d.statusIndex > 0 ? L.STATUSES[d.statusIndex - 1] : "",
      typeSel: d.typeSel,
      keyword: d.keyword,
      conds: d.conditions,
      condMode: d.condMode,
      primary: L.SORT_FIELDS[d.primaryIdx].key,
      primaryAsc: d.primaryAsc,
      secondary: L.SORT_FIELDS[d.secondaryIdx].key,
      secondaryAsc: d.secondaryAsc,
    });
    this.setData({
      list: out.slice(0, d.visibleCount).map(L.decorate),
      filteredCount: out.length,
    });
    this.refreshCounts();
  },

  // ---------- 事件 ----------
  onTab: function (e) {
    this.setData({ group: e.currentTarget.dataset.key, visibleCount: PAGE_SIZE });
    this.apply();
  },
  onSearch: function (e) {
    const that = this;
    this.setData({ keyword: e.detail.value });
    clearTimeout(this._kt);
    this._kt = setTimeout(function () {
      that.setData({ visibleCount: PAGE_SIZE });
      that.apply();
    }, 250);
  },
  onStatus: function (e) {
    const idx = Number(e.detail.value); // 0=全部, 1~5=具体状态
    this.setData({ statusIndex: idx, visibleCount: PAGE_SIZE });
    this.apply();
  },
  toggleTypePanel: function () {
    this.setData({ typePanelOpen: !this.data.typePanelOpen, condPanelOpen: false });
  },
  toggleCondPanel: function () {
    this.setData({ condPanelOpen: !this.data.condPanelOpen, typePanelOpen: false });
  },
  closePanels: function () {
    this.setData({ typePanelOpen: false, condPanelOpen: false });
  },
  noop: function () {},
  onTypeChange: function (e) {
    const sel = e.detail.value;
    const items = this.data.typeItems.map(function (t) {
      return { name: t.name, checked: sel.indexOf(t.name) >= 0 };
    });
    this.setData({ typeSel: sel, typeItems: items, visibleCount: PAGE_SIZE });
    this.apply();
  },
  clearTypes: function () {
    const items = this.data.typeItems.map(function (t) {
      return { name: t.name, checked: false };
    });
    this.setData({ typeSel: [], typeItems: items, visibleCount: PAGE_SIZE });
    this.apply();
  },
  onPrimary: function (e) {
    this.setData({ primaryIdx: Number(e.detail.value), visibleCount: PAGE_SIZE });
    this.apply();
  },
  onSecondary: function (e) {
    this.setData({ secondaryIdx: Number(e.detail.value), visibleCount: PAGE_SIZE });
    this.apply();
  },
  togglePrimaryDir: function () {
    this.setData({ primaryAsc: !this.data.primaryAsc, visibleCount: PAGE_SIZE });
    this.apply();
  },
  toggleSecondaryDir: function () {
    this.setData({ secondaryAsc: !this.data.secondaryAsc, visibleCount: PAGE_SIZE });
    this.apply();
  },
  onCondMode: function (e) {
    this.setData({ condMode: e.detail.value, visibleCount: PAGE_SIZE });
    this.apply();
  },
  addCond: function () {
    const c = this.data.conditions.concat([
      { metric: "y1", metricLabel: "近1年收益", op: ">", value: "" },
    ]);
    this.setData({ conditions: c, visibleCount: PAGE_SIZE });
    this.apply();
  },
  delCond: function (e) {
    const i = Number(e.currentTarget.dataset.idx);
    const c = this.data.conditions.slice();
    c.splice(i, 1);
    this.setData({ conditions: c, visibleCount: PAGE_SIZE });
    this.apply();
  },
  onCondMetric: function (e) {
    const i = Number(e.currentTarget.dataset.idx);
    const c = this.data.conditions.slice();
    const m = L.METRICS[Number(e.detail.value)];
    c[i].metric = m.key;
    c[i].metricLabel = m.label;
    this.setData({ conditions: c, visibleCount: PAGE_SIZE });
    this.apply();
  },
  onCondOp: function (e) {
    const i = Number(e.currentTarget.dataset.idx);
    const c = this.data.conditions.slice();
    c[i].op = this.data.ops[Number(e.detail.value)];
    this.setData({ conditions: c, visibleCount: PAGE_SIZE });
    this.apply();
  },
  onCondValue: function (e) {
    const i = Number(e.currentTarget.dataset.idx);
    const c = this.data.conditions.slice();
    c[i].value = e.detail.value;
    this.setData({ conditions: c, visibleCount: PAGE_SIZE });
    this.apply();
  },

  toggleCard: function (e) {
    const code = e.currentTarget.dataset.code;
    const patch = {};
    patch["expanded." + code] = !this.data.expanded[code];
    this.setData(patch);
  },

  copyCode: function (e) {
    wx.setClipboardData({ data: e.currentTarget.dataset.code });
  },

  onReachBottom: function () {
    if (this.data.visibleCount < this.data.filteredCount) {
      this.setData({ visibleCount: this.data.visibleCount + PAGE_SIZE });
      this.apply();
    }
  },

  onPullDownRefresh: function () {
    this.load();
    wx.stopPullDownRefresh();
  },
});
