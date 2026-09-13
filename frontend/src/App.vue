<script setup>
import { ref } from "vue";
import ListPage from "./components/ListPage.vue";
import WatchPage from "./components/WatchPage.vue";

const tab = ref("bond");
</script>

<template>
  <ListPage v-if="tab === 'bond'" module="bond" />
  <ListPage v-else-if="tab === 'qdii'" module="qdii" />
  <WatchPage v-else />

  <nav class="tabbar">
    <button class="tbtn" :class="{ on: tab === 'bond' }" @click="tab = 'bond'">
      <span class="ticon">📊</span><span class="tlabel">债基</span>
    </button>
    <button class="tbtn" :class="{ on: tab === 'qdii' }" @click="tab = 'qdii'">
      <span class="ticon">🌍</span><span class="tlabel">QDII</span>
    </button>
    <button class="tbtn" :class="{ on: tab === 'watch' }" @click="tab = 'watch'">
      <span class="ticon">⭐</span><span class="tlabel">自选</span>
    </button>
  </nav>
</template>
