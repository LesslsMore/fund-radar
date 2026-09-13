<script setup>
import { ref } from "vue";

const props = defineProps({
  f: { type: Object, required: true },
  watched: { type: Boolean, default: false },
  showStar: { type: Boolean, default: true },
});
const emit = defineEmits(["toggle-watch"]);
const open = ref(false);

const sgztClass = ref(props.f.sgztCls); // decorate() 已预计算
function pct(v) {
  if (v === "" || v == null) return { text: "--", cls: "muted" };
  const n = parseFloat(v);
  if (Number.isNaN(n)) return { text: v + "%", cls: "muted" };
  return { text: (n > 0 ? "+" : "") + n.toFixed(2) + "%", cls: n > 0 ? "pos" : n < 0 ? "neg" : "muted" };
}
const y1 = ref(pct(props.f.y1));
const y2 = ref(pct(props.f.y2));
const y3 = ref(pct(props.f.y3));
const num2 = (v) => {
  const n = parseFloat(v);
  return Number.isNaN(n) ? "--" : n.toFixed(2);
};
</script>

<template>
  <div class="card" @click="open = !open">
    <div class="l1">
      <span class="name">{{ f.name }}</span>
      <span :class="sgztClass">{{ f.sgzt || "未知" }}</span>
      <span v-if="showStar" class="star" :class="{ on: watched }"
            @click.stop="emit('toggle-watch')">{{ watched ? "★" : "☆" }}</span>
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
      <div class="kv"><div class="k">夏普 近1年</div><div class="v">{{ num2(f.sharpe_1y) }}</div></div>
      <div class="kv"><div class="k">夏普 近2年</div><div class="v">{{ num2(f.sharpe_2y) }}</div></div>
      <div class="kv"><div class="k">夏普 近3年</div><div class="v">{{ num2(f.sharpe_3y) }}</div></div>
      <div class="kv"><div class="k">标准差 近1年</div><div class="v">{{ f.std1 }}</div></div>
    </div>
    <div class="l3">
      <span>{{ f.type }}</span>
      <span>净值 {{ f.navText }} ({{ f.nav_date }})</span>
      <span>费率 {{ f.feeText }}</span>
    </div>

    <div v-if="open" class="detail" @click.stop>
      <div class="dgrid">
        <div class="cell" v-for="cell in f.detailCells" :key="cell.k">
          <div class="k">{{ cell.k }}</div><div class="dv" :class="cell.cls">{{ cell.text }}</div>
        </div>
        <div class="cell"><div class="k">夏普 近2/3年</div><div class="dv">{{ num2(f.sharpe_2y) }} / {{ num2(f.sharpe_3y) }}</div></div>
        <div class="cell"><div class="k">购买起点</div><div class="dv">{{ f.minBuyText }}</div></div>
        <div class="cell"><div class="k">赎回状态</div><div class="dv">{{ f.shzt || "--" }}</div></div>
        <div class="cell"><div class="k">下一开放日</div><div class="dv">{{ f.next_open_day || "--" }}</div></div>
      </div>
      <div class="actions">
        <a :href="`http://fund.eastmoney.com/${f.code}.html`" target="_blank" rel="noopener">天天基金档案</a>
        <a :href="`https://fundf10.eastmoney.com/tsdata_${f.code}.html`" target="_blank" rel="noopener">风险指标</a>
      </div>
    </div>
  </div>
</template>
