<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({ f: { type: Object, required: true } });
const open = ref(false);

const sgztClass = computed(() => {
  const s = props.f.sgzt;
  if (s === '开放申购') return 'badge open';
  if (s === '限大额') return 'badge big';
  if (s === '暂停申购') return 'badge pause';
  if (s === '封闭期' || s === '认购期') return 'badge close';
  return 'badge';
});

function pct(v) {
  if (v === '' || v == null) return { text: '--', cls: 'muted' };
  const n = parseFloat(v);
  if (Number.isNaN(n)) return { text: v + '%', cls: 'muted' };
  return { text: (n > 0 ? '+' : '') + n.toFixed(2) + '%', cls: n > 0 ? 'pos' : n < 0 ? 'neg' : 'muted' };
}
const y1 = computed(() => pct(props.f.y1));
const y2 = computed(() => pct(props.f.y2));
const y3 = computed(() => pct(props.f.y3));
const cells = computed(() => {
  const f = props.f;
  return [
    ['近1周', pct(f.w)], ['近1月', pct(f.m1)], ['近3月', pct(f.m3)],
    ['近6月', pct(f.m6)], ['近1年', pct(f.y1)], ['近2年', pct(f.y2)],
    ['近3年', pct(f.y3)], ['今年来', pct(f.ytd)], ['成立来', pct(f.since)],
  ];
});
const num = (v, digits) => {
  if (v === '' || v == null) return '--';
  const n = parseFloat(v);
  return Number.isNaN(n) ? v : n.toFixed(digits ?? 2);
};
</script>

<template>
  <div class="card" @click="open = !open">
    <div class="l1">
      <span class="name">{{ f.name }}</span>
      <span :class="sgztClass">{{ f.sgzt || '未知' }}</span>
      <span class="code">{{ f.code }}</span>
    </div>
    <div class="l2">
      <div class="kv">
        <div class="k">日累计限额</div>
        <div class="v" :class="f.limit_group === 'limited' ? 'limit' : 'unlim'">{{ f.limit_display }}</div>
      </div>
      <div class="kv"><div class="k">近1年收益</div><div class="v" :class="y1.cls">{{ y1.text }}</div></div>
      <div class="kv"><div class="k">近2年收益</div><div class="v" :class="y2.cls">{{ y2.text }}</div></div>
      <div class="kv"><div class="k">近3年收益</div><div class="v" :class="y3.cls">{{ y3.text }}</div></div>
    </div>
    <div class="l2">
      <div class="kv"><div class="k">夏普 近1年</div><div class="v">{{ num(f.sharpe_1y) }}</div></div>
      <div class="kv"><div class="k">夏普 近2年</div><div class="v">{{ num(f.sharpe_2y) }}</div></div>
      <div class="kv"><div class="k">夏普 近3年</div><div class="v">{{ num(f.sharpe_3y) }}</div></div>
      <div class="kv"><div class="k">标准差 近1年</div><div class="v">{{ f.std_1y || '--' }}</div></div>
    </div>
    <div class="l3">
      <span>{{ f.type }}</span>
      <span>净值 {{ num(f.nav, 4) }} ({{ f.nav_date }})</span>
      <span>手续费 {{ f.fee_rate || '--' }}</span>
    </div>

    <div v-if="open" class="detail" @click.stop>
      <div class="grid">
        <div class="cell" v-for="[k, v] in cells" :key="k">
          <div class="k">{{ k }}</div>
          <div class="v" :class="v.cls">{{ v.text }}</div>
        </div>
        <div class="cell"><div class="k">标准差(近1年)</div><div class="v">{{ f.std_1y || '--' }}</div></div>
        <div class="cell"><div class="k">夏普(近2年/3年)</div><div class="v">{{ num(f.sharpe_2y) }} / {{ num(f.sharpe_3y) }}</div></div>
        <div class="cell"><div class="k">购买起点</div><div class="v">{{ f.min_buy != null ? f.min_buy + '元' : '--' }}</div></div>
        <div class="cell"><div class="k">赎回状态</div><div class="v">{{ f.shzt || '--' }}</div></div>
        <div class="cell"><div class="k">下一开放日</div><div class="v">{{ f.next_open_day || '--' }}</div></div>
      </div>
      <div class="actions">
        <a :href="`http://fund.eastmoney.com/${f.code}.html`" target="_blank" rel="noopener">天天基金档案</a>
        <a :href="`https://fundf10.eastmoney.com/tsdata_${f.code}.html`" target="_blank" rel="noopener">风险指标</a>
      </div>
    </div>
  </div>
</template>
