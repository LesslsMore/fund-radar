// API 客户端: 与网页版共用同一套后端接口 (Netlify 部署, 国内可直连)
// 正式发布小程序前需将域名换成已备案域名, 并在 mp 后台配置 request 合法域名
const BASE = "https://fund-radar-lsm.netlify.app";

function request(path, params) {
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
      url: BASE + path + qs,
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

module.exports = {
  BASE: BASE,
  getMeta: function () {
    return request("/api/meta");
  },
  getFunds: function (params) {
    return request("/api/funds", params);
  },
  getFund: function (code) {
    return request("/api/funds/" + code);
  },
};
