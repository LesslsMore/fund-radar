<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  page: { type: Number, required: true },
  pageCount: { type: Number, required: true },
});
const emit = defineEmits(["go"]);
const jump = ref("");

watch(
  () => props.page,
  () => (jump.value = "")
);

function go(p) {
  const n = parseInt(p, 10);
  if (!Number.isNaN(n) && n >= 1 && n <= props.pageCount && n !== props.page) emit("go", n);
}
</script>

<template>
  <div class="pager">
    <button class="pgbtn" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
    <span class="pgtext">{{ page }} / {{ pageCount }}</span>
    <button class="pgbtn" :disabled="page >= pageCount" @click="go(page + 1)">下一页</button>
    <span class="pgjump">
      <input class="pgin" type="number" min="1" :max="pageCount" v-model="jump" @keyup.enter="go(jump)" />
      <button class="pgbtn" @click="go(jump)">跳转</button>
    </span>
  </div>
</template>
