import { createApp } from 'vue';
import App from './App.vue';
import { registerSW } from 'virtual:pwa-register';
import './style.css';

const updateSW = registerSW({
  onNeedRefresh() {
    // 有新版本(新数据)时提示一次, 用户点击刷新
    const bar = document.createElement('div');
    bar.className = 'update-bar';
    bar.textContent = '🔄 数据已更新，点击刷新';
    bar.onclick = () => updateSW(true);
    document.body.appendChild(bar);
  }
});

createApp(App).mount('#app');
