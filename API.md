# API 文档（含微信小程序对接说明）

所有接口均为 `GET`，返回统一 JSON 信封，UTF-8，支持 CORS（`*`）：

```json
{ "code": 0, "data": { ... }, "message": "ok" }
```

- `code = 0` 成功；非 0 为 HTTP 状态码同值错误。
- 响应带 `Cache-Control: public, max-age=300`，CDN 与 PWA 均可缓存。
- 域名：部署后为 `https://<project>.vercel.app`（也可绑定自定义域名）。

## GET /api/meta

数据概况。

```json
{
  "code": 0,
  "data": {
    "built_at": "2026-09-12 20:31:16",   // 数据库构建时间
    "data_date": "09-11",                 // 净值日期 (MM-DD)
    "funds_total": "27526",
    "db_scope": "all",
    "bond_total": "7332",
    "limited_total": "3752",
    "unlimited_total": "19661",
    "nodata_total": "4113",
    "returns_total": "22753",
    "risk_total": "7332",
    "bond_by_group": [ { "g": "limited", "n": 2023, "open_n": 0, "big_n": 1195 }, ... ],
    "bond_by_type":  [ { "type": "债券型-长债", "n": 2766 }, ... ]
  }
}
```

## GET /api/funds

列表查询，全部参数可选。

| 参数 | 取值 | 说明 |
|---|---|---|
| `scope` | `bond`(默认) / `all` | 只看债券型 / 全部 27526 只 |
| `group` | `limited` / `unlimited` / `nodata` | 限额分组 |
| `status` | `开放申购` `限大额` `暂停申购` `封闭期` `认购期` | 申购状态精确匹配 |
| `type` | 如 `长债` | 基金类型 LIKE 匹配 |
| `q` | 任意词 | 按名称/代码 LIKE 搜索 |
| `sort` | `default` `limit_asc` `limit_desc` `y1_desc` `y1_asc` `sharpe_desc` | 排序（缺值排最后） |
| `page` / `page_size` | 数字（page_size ≤ 1000） | 分页 |
| `all=1` | - | 一次取全部（≤2 万条），前端 PWA 用 |

示例：

```
/api/funds?group=limited&status=限大额&sort=y1_desc&page_size=20
/api/funds?q=转债&sort=sharpe_desc
/api/funds?scope=bond&all=1
```

`items[]` 单条字段：

```json
{
  "code": "006431", "name": "汇安鼎利纯债A", "type": "债券型-长债",
  "sgzt": "限大额", "shzt": "开放赎回", "next_open_day": "",
  "min_buy": 100, "daily_limit": 100,
  "limit_group": "limited", "limit_display": "100元",
  "fee_rate": "0.08%", "nav": "1.1979", "nav_date": "09-11", "is_bond": 1,
  "w": "", "m1": "3.19", "m3": "-13.03", "m6": "28.44", "y1": "79.38",
  "y2": "...", "y3": "...", "ytd": "...", "since": "...",
  "ret_source": "rank",                      // rank | pingzhongdata
  "sharpe_1y": "7.26", "sharpe_2y": "1.72", "sharpe_3y": "2.68",
  "std_1y": "0.43%", "std_2y": "...", "std_3y": "...", "as_of": "2026-09-11"
}
```

## GET /api/funds/:code

单只基金完整记录，字段同上。示例：`/api/funds/006431`。

## 微信小程序对接预留

后端即为标准 HTTPS REST，未来小程序端可直接复用，无需任何后端改动：

1. 在小程序公众平台「开发设置 → 服务器域名 → request 合法域名」添加
   `https://<project>.vercel.app`（须为 HTTPS，Vercel 默认满足）。
2. 调用示例（与前端 `src/api/client.js` 同一套路径与信封）：

```js
wx.request({
  url: 'https://<project>.vercel.app/api/funds',
  data: { group: 'limited', status: '限大额', sort: 'limit_asc', page: 1, page_size: 20 },
  success: (res) => {
    if (res.data.code === 0) console.log(res.data.data.items);
  }
});
```

3. 建议：小程序与 PWA 共用 `page/page_size` 分页模式；`all=1` 大响应留给浏览器场景。
4. 注意：`request` 合法域名要求 ICP 备案的域名（用自定义域名接入时），`vercel.app`
   域名仅适合开发调试；正式上线小程序可绑定已备案域名（域名本身成本约几十元/年，其余仍为 0）。
