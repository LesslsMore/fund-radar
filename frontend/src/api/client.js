// API 客户端 —— 与后端耦合的唯一入口。
// 未来微信小程序 wx.request 直接复用这里的路径与参数即可（见根目录 API.md）。
const BASE = import.meta.env.VITE_API_BASE || '';

async function get(path, params) {
  const qs = params ? '?' + new URLSearchParams(params) : '';
  const res = await fetch(BASE + path + qs);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  if (body.code !== 0) throw new Error(body.message || '接口错误');
  return body.data;
}

export const getMeta = () => get('/api/meta');
export const getFunds = (params) => get('/api/funds', params);
export const getFund = (code) => get(`/api/funds/${code}`);
