// 云函数: proxy —— 转发请求基金雷达后端 API (腾讯云服务器出网, 无域名白名单限制)
// 小程序端传 { path: "/api/funds", params: { group: "limited", page_size: 1000 } }
// 返回后端的统一信封 { code, data, message }
const BASE = "https://fund-radar-cf.pages.dev";

exports.main = async (event) => {
  const path = String(event.path || "/api/meta");
  if (!path.startsWith("/api/")) {
    return { code: 403, data: null, message: "forbidden path" };
  }
  let qs = "";
  if (event.params && typeof event.params === "object") {
    const parts = [];
    for (const k of Object.keys(event.params)) {
      const v = event.params[k];
      if (v !== "" && v != null) parts.push(k + "=" + encodeURIComponent(v));
    }
    if (parts.length) qs = "?" + parts.join("&");
  }
  const url = BASE + path + qs;

  return new Promise((resolve) => {
    const req = require("https")
      .get(url, { timeout: 25000 }, (res) => {
        let raw = "";
        res.on("data", (chunk) => (raw += chunk));
        res.on("end", () => {
          try {
            resolve(JSON.parse(raw));
          } catch (e) {
            resolve({ code: res.statusCode, data: null, message: "non-json response" });
          }
        });
      })
      .on("timeout", () => {
        req.destroy();
        resolve({ code: 504, data: null, message: "upstream timeout" });
      })
      .on("error", (e) => {
        resolve({ code: 502, data: null, message: "upstream error: " + e.message });
      });
    req.end();
  });
};
