// API 客户端: 双通道
// - 云通道 (推荐): wx.cloud.callFunction 走代理云函数, 免域名校验/免备案, 真机+上线前可用
//   需在 config.js 填 CLOUD_ENV_ID 并部署 cloudfunctions/proxy
// - 直连: wx.request 直连后端, 需合法域名或开发者工具调试模式
const config = require("../config.js");

const CLOUD_READY = !!(config.CLOUD_ENV_ID && typeof wx !== "undefined" && wx.cloud);

// 大响应不能走云通道 (云函数返回上限约 1MB), 全量列表改分页拉取
async function getFunds(params) {
  if (CLOUD_READY) {
    const p = Object.assign({}, params);
    if (p.all === "1" || p.all === 1) {
      delete p.all;
      p.page_size = 1000;
      let page = 1;
      let items = [];
      let total = Infinity;
      while (items.length < total) {
        const d = await callCloud("/api/funds", Object.assign({}, p, { page: page }));
        total = d.total;
        items = items.concat(d.items);
        if (!d.items || d.items.length === 0) break;
        page++;
      }
      return { items: items, total: items.length };
    }
    return callCloud("/api/funds", p);
  }
  return direct("/api/funds", params);
}

function getMeta() {
  return CLOUD_READY ? callCloud("/api/meta") : direct("/api/meta");
}

function getFund(code) {
  return CLOUD_READY ? callCloud("/api/funds/" + code) : direct("/api/funds/" + code);
}

function callCloud(path, params) {
  return new Promise(function (resolve, reject) {
    wx.cloud.callFunction({
      name: "proxy",
      data: { path: path, params: params || {} },
      success: function (r) {
        const body = r.result;
        if (body && body.code === 0) resolve(body.data);
        else reject(new Error((body && body.message) || "云函数返回异常"));
      },
      fail: function (e) {
        reject(new Error(e.errMsg || "云函数调用失败"));
      },
    });
  });
}

function direct(path, params) {
  return new Promise(function (resolve, reject) {
    let qs = "";
    if (params) {
      const parts = [];
      for (const k in params) {
        if (params[k] !== "" && params[k] != null) parts.push(k + "=" + encodeURIComponent(params[k]));
      }
      if (parts.length) qs = "?" + parts.join("&");
    }
    wx.request({
      url: apiBase() + path + qs,
      success: function (r) {
        if (r.statusCode === 200 && r.data && r.data.code === 0) resolve(r.data.data);
        else reject(new Error((r.data && r.data.message) || "HTTP " + r.statusCode));
      },
      fail: function (e) {
        reject(new Error(e.errMsg || "网络请求失败"));
      },
    });
  });
}

function apiBase() {
  return "https://fund-radar-lsm.netlify.app";
}

module.exports = {
  getMeta: getMeta,
  getFunds: getFunds,
  getFund: getFund,
  CLOUD_READY: CLOUD_READY,
  BASE: apiBase(),
};
