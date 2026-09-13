import { createApp } from 'vue';
import App from './App.vue';
import { registerSW } from 'virtual:pwa-register';
import './style.css';

// 自动更新: 新版本 SW 自动接管, 下次打开即最新 (避免旧缓存卡住)
registerSW({ immediate: true });

createApp(App).mount('#app');
