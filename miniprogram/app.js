const config = require("./config.js");

// 云开发初始化 (config.js 填了环境 ID 才启用云通道)
if (config.CLOUD_ENV_ID && wx.cloud) {
  wx.cloud.init({ env: config.CLOUD_ENV_ID, traceUser: false });
}

App({});
