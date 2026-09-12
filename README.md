# 📊 债基限额雷达

手机网页（PWA）浏览 **债券型基金的申购限额 · 阶段收益 · 夏普比率**，支持按限额分组/申购状态/类型/关键词筛选排序。
数据每日自动爬取自天天基金，存入 SQLite，通过 Serverless API 读取。**全程 0 元、无需自己的服务器。**

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions (定时 cron, 免费额度)                             │
│    每天 01:30 (北京) 自动运行 pipeline/ 四个爬虫脚本               │
│    申购状态551页 → 解析筛选 → 排行接口(收益) → F10(夏普/标准差)      │
│    → build_db.py 重建 api/db/funds.db → 提交推送                  │
│                          │ git push                             │
│                          ▼                                        │
│  Vercel (免费 Hobby) 自动重新部署                                  │
│    前端: frontend/ → Vite + Vue3 + vite-plugin-pwa 静态托管        │
│    后端: api/     → Serverless 函数, 只读打开打包内的 SQLite        │
│                          │                                       │
│     手机浏览器(可安装到桌面/离线可用) ── 未来微信小程序 ──┘            │
└─────────────────────────────────────────────────────────────────┘
```

> **为什么 SQLite 放在 git 里？** Vercel/Render 免费版的文件系统是临时的（函数实例随时重建，
> 重启即丢盘），SQLite 无法常驻。把数据库作为"构建产物"随代码一起提交，是最稳的零成本方案：
> 爬取 = 定时提交，部署 = git push 自动触发，天然幂等、可回滚、有完整历史。

## 目录结构

```
fund-radar/
├── api/                       # Vercel Serverless (Node 22 + better-sqlite3)
│   ├── db/funds.db            #   SQLite 数据库(提交进仓库, 每日由 Actions 重建)
│   ├── _lib.js                #   开库/查询构造(全部参数白名单)
│   ├── funds.js               #   GET /api/funds      列表(筛选/排序/分页)
│   ├── funds/[code].js        #   GET /api/funds/:code 单只详情
│   └── meta.js                #   GET /api/meta       数据日期/计数
├── frontend/                  # Vite + Vue3 + vite-plugin-pwa
│   └── src/
│       ├── App.vue            #   筛选页: 分组/状态/类型/搜索/排序 + 无限滚动
│       ├── components/FundCard.vue
│       └── api/client.js      #   API 调用唯一入口(小程序可复用同一套路径)
├── pipeline/                  # 定时爬取流水线 (GitHub Actions 运行)
│   ├── scrape_all.py          #   申购状态 551 页 (t=8 接口)
│   ├── parse_and_filter.py    #   解析 + 债券筛选 + 限额分组
│   ├── fetch_returns.py       #   排行接口 102 页(阶段涨幅) + pingzhongdata 补漏
│   ├── fetch_sharpe.py        #   F10 特色数据页(夏普/标准差)
│   ├── build_db.py            #   中间数据 → SQLite
│   └── .cache/                #   本地种子缓存(gitignore)
├── .github/workflows/update.yml  # 定时任务(北京 01:30) + 手动触发
├── vercel.json                # 构建/函数配置
├── local-server.mjs           # 本地联调: 静态 dist + /api 同源
└── API.md                     # 接口文档(小程序对接指南)
```

## 5 分钟部署（全部免费）

1. **推到 GitHub**：`git init && git add -A && git commit -m "init" && git remote add origin ... && git push`
   （public 仓库 Actions 无限免费；private 也够用，本工作流每天约 25 分钟）
2. **Vercel 导入**：[vercel.com/new](https://vercel.com/new) 选择该仓库 → 直接 Deploy。
   `vercel.json` 已配置好前后端构建，无需改任何设置。
3. 完成。之后每天 Actions 自动爬取并提交新 `funds.db`，Vercel 检测到推送自动重新部署；
   PWA 检测到新数据提示刷新。

**可选环境变量**（Vercel/Actions 设置里加）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `DB_SCOPE` | `all` | SQLite 存 `all`=全量 27526 只（约 8MB/天）或 `bond`=仅 7332 只债券型（约 2.5MB/天）。在意 GitHub 仓库体积增长时用 `bond` |

## 本地开发

```bash
npm install                        # api 依赖 (better-sqlite3)
cd frontend && npm install && npm run build && cd ..
node local-server.mjs              # http://localhost:3000  (前端+API 同源)
```

重新生成数据库（用最新爬取数据）：
```bash
cd pipeline
python scrape_all.py && python parse_and_filter.py && python fetch_returns.py && python fetch_sharpe.py && python build_db.py
```
（各脚本支持断点续传，输出目录可用 `FUND_RAW_DIR/FUND_INTER_DIR/FUND_OUT_DIR` 覆盖）

## 数据口径

- **有限额**（limited）：申购状态代码 1~10 且 0 ≤ 日累计限额 < 8 亿 —— 网页端会显示具体限额
- **无限额**（unlimited）：限额 ≥ 8 亿（网页端显示"无限额"，存储值多为 1000 亿哨兵）；
  含少量"限大额"状态但限额 ≥8 亿的基金，看 `sgzt` 字段区分
- **无数据**（nodata）：状态码无效（网页端显示"---"），含认购期等
- 夏普比率/标准差来源为天天基金 F10"特色数据"（与同花顺口径不同，只做横向比较）
- 收益/夏普缺值 = 成立不满一年或源数据无（站点显示"--"）
- 详细字段与验证过程见 `../fund_data/README.md`

## 成本清单

| 项目 | 方案 | 费用 |
|---|---|---|
| 前端托管 + API | Vercel Hobby | 0 |
| 定时爬取 | GitHub Actions（public 仓库无限 / private 每天~25min） | 0 |
| 数据库 | SQLite 文件随仓库分发，无独立数据库服务 | 0 |
| 域名 | vercel.app 子域 | 0 |
