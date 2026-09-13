# 基金雷达 · 微信小程序版

原生微信小程序（WXML/WXSS/JS，无第三方框架、无构建步骤），与网页版共用同一套后端 API 和业务逻辑
（筛选/排序/条件判断逻辑在 `utils/fund-logic.js`，为平台无关的纯 JS）。

## 快速运行（5 分钟）

1. **注册小程序账号拿 AppID**（个人主体免费）：
   [mp.weixin.qq.com](https://mp.weixin.qq.com/) → 立即注册 → 小程序 → 用未绑定过公众版的邮箱注册，
   完成主体登记后，在「设置 → 基本设置」里能看到 AppID。
   *（只是先在本地跑起来的话，也可以跳过这步，导入时选"测试号"。）*
2. **下载微信开发者工具**（稳定版）：
   [developer.weixin.qq.com/miniprogram/dev/devtools/download.html](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
3. **导入项目**：打开开发者工具 → 导入 → 选择本目录（`miniprogram/`）→ AppID 填你的（或测试号）→ 确定。
4. **勾选不校验域名**（开发阶段必须）：右上角「详情 → 本地设置」→ 勾选
   **「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」**。
   本项目当前请求 `https://fund-radar-lsm.netlify.app`（未备案域名），不勾选会请求失败。
5. 模拟器里即可看到完整功能；点「预览」扫码可在手机上真机运行（同样需要第 4 步设置）。

## 功能（与网页版一致）

- 分组标签（有限额/无限额/无数据/全部）+ 计数
- 申购状态、类型多选（面板勾选，如 中短债+长债）、关键词搜索
- **两级排序**（第一/第二排序键 + 各自升降序按钮）
- **条件筛选**（多条件 + 满足任一/全部满足，例：近1年收益>3% 或 近2年收益>2.5%）
- 卡片展开九段涨幅明细、下拉刷新、触底自动加载更多

## 正式发布（上线给所有人用）

1. **服务器域名（硬约束）**：小程序的 `request` 合法域名**必须为 HTTPS + ICP 备案域名**。
   `netlify.app` / `vercel.app` / `pages.dev` 都不能用于正式发布。
   - 开发/体验阶段：用第 4 步的"不校验域名"即可，无需备案；
   - 正式发布：需要自备一个已备案域名指向本应用后端（或在国内平台重建后端）。
2. 代码里改接口地址：`utils/api.js` 顶部的 `BASE`。
3. 开发者工具右上角「上传」→ mp 后台「版本管理」→ 提交审核（类目建议：工具 → 信息查询）
   → 审核通过后「发布」。个人主体可发布，但不能含商业内容。

## 目录结构

```
miniprogram/
├── app.json / app.js / app.wxss / sitemap.json
├── project.config.json     # appid 占位 touristappid, urlCheck 已关
├── utils/
│   ├── api.js              # wx.request 封装 (BASE 在这里改)
│   └── fund-logic.js       # 平台无关业务逻辑 (筛选/排序/条件/展示装饰)
└── pages/index/            # 单页: 筛选 + 列表 + 详情展开
```
