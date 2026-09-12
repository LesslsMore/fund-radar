# -*- coding: utf-8 -*-
"""
把爬取产物(pipeline/.cache/ 下的中间数据)构建为 SQLite 数据库 -> api/db/funds.db

表结构:
  funds   id PK, code UNIQUE, name, type, sgzt, shzt, next_open_day, min_buy,
          daily_limit, limit_group, limit_display, fee_flag, buy_code, fee_rate,
          nav, nav_date, is_bond, sort_order          -- 全量 27526 只
  returns code PK, w, m1, m3, m6, y1, y2, y3, ytd, since, source, nav_date2
  risk    code PK, std_1y, std_2y, std_3y, sharpe_1y, sharpe_2y, sharpe_3y, as_of
  meta    key PK, value   (data_date / built_at / 各计数)

limit_group 口径(与网页端展示一致):
  limited=有限额(状态码1~10且0<=限额<8亿) unlimited=无限额(>=8亿) nodata=无数据(状态码无效等)
"""
import json
import os
import csv
import sqlite3
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.environ.get("FUND_INTERMEDIATE_DIR", os.path.join(BASE, "pipeline", ".cache"))
DB_DIR = os.path.join(BASE, "api", "db")
os.makedirs(DB_DIR, exist_ok=True)
DB = os.path.join(DB_DIR, "funds.db")

BUYABLE = {str(i) for i in range(1, 11)}
UNLIM = 8 * 1e8
PERIODS = {"近1周": "w", "近1月": "m1", "近3月": "m3", "近6月": "m6",
           "近1年": "y1", "近2年": "y2", "近3年": "y3", "今年来": "ytd", "成立来": "since"}


def load_json(name):
    p = os.path.join(CACHE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def main():
    funds = load_json("all_funds.json")
    db_scope = os.environ.get("DB_SCOPE", "all")  # all=全量27526 | bond=仅债券基金(省仓库体积)
    if db_scope == "bond":
        funds = [f for f in funds if f["债券型"]]
    print(f"all_funds: {len(funds)} (DB_SCOPE={db_scope})")

    rank = {}
    rp = os.path.join(CACHE, "rank_all_funds_returns.csv")
    if os.path.exists(rp):
        for r in csv.DictReader(open(rp, encoding="utf-8-sig")):
            rank[r["基金代码"]] = r
    patched = load_json("patched_returns.json")
    returns_src = dict(rank)
    returns_src.update({c: v for c, v in patched.items() if isinstance(v, dict) and v})
    sharpe = load_json("sharpe_parsed.json")

    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript("""
    PRAGMA journal_mode=DELETE;
    CREATE TABLE funds(
      id INTEGER PRIMARY KEY, code TEXT UNIQUE, name TEXT, type TEXT,
      sgzt TEXT, shzt TEXT, next_open_day TEXT, min_buy REAL,
      daily_limit REAL, limit_group TEXT, limit_display TEXT,
      fee_flag TEXT, buy_code TEXT, fee_rate TEXT, nav TEXT, nav_date TEXT,
      is_bond INTEGER, sort_order INTEGER);
    CREATE INDEX idx_funds_bond ON funds(is_bond, limit_group, sort_order);
    CREATE INDEX idx_funds_type ON funds(type);
    CREATE TABLE returns(
      code TEXT PRIMARY KEY, w TEXT, m1 TEXT, m3 TEXT, m6 TEXT,
      y1 TEXT, y2 TEXT, y3 TEXT, ytd TEXT, since TEXT, source TEXT, nav_date2 TEXT);
    CREATE TABLE risk(
      code TEXT PRIMARY KEY, std_1y TEXT, std_2y TEXT, std_3y TEXT,
      sharpe_1y TEXT, sharpe_2y TEXT, sharpe_3y TEXT, as_of TEXT);
    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)

    data_date = ""
    rows = []
    returns_rows = []
    risk_rows = []
    limited = []  # (limit, code)
    groups = {"limited": [], "unlimited": [], "nodata": []}
    for f in funds:
        code = f["基金代码"]
        raw = f["日累计申购限额_元"]
        buyable = str(f["申购状态代码"]) in BUYABLE
        if f["有限额"]:
            g, disp = "limited", f["限额展示"]
        elif buyable and raw >= UNLIM:
            g, disp = "unlimited", "无限额"
        else:
            g, disp = "nodata", "---"
        if g != "nodata":
            raw_out = int(raw) if raw == int(raw) else raw
        else:
            raw_out = None
        groups[g].append((code, raw))
        rows.append((code, f["基金简称"], f["基金类型"], f["申购状态"], f["赎回状态"],
                     f["下一开放日"], f["购买起点_元"], raw_out, g, disp,
                     f["费率标志"], f["申购状态代码"], f["手续费率"], f["最新净值"], f["净值日期"],
                     1 if f["债券型"] else 0, None))
        rv = returns_src.get(code)
        if isinstance(rv, dict) and rv:
            nav_date2 = rank.get(code, {}).get("净值日期", "")
            returns_rows.append((code, *[rv.get(zh, "") for zh in PERIODS],
                                 "rank" if code in rank else "pingzhongdata", nav_date2))
        sv = sharpe.get(code)
        if isinstance(sv, dict) and sv.get("_status") == "ok":
            risk_rows.append((code, sv.get("标准差_近1年%", ""), sv.get("标准差_近2年%", ""),
                              sv.get("标准差_近3年%", ""), sv.get("夏普比率_近1年", ""),
                              sv.get("夏普比率_近2年", ""), sv.get("夏普比率_近3年", ""),
                              sv.get("风险指标截止日", "")))
        if not data_date and f["净值日期"]:
            pass
    # 排序: limited 按限额升序 -> unlimited 按代码 -> nodata 按代码; 非|债券|基金排最后
    def sort_key(item):
        code, raw = item
        return (raw if 0 <= raw < UNLIM else UNLIM, code)
    order_map = {}
    idx = 0
    for g in ("limited", "unlimited", "nodata"):
        for code, _raw in sorted(groups[g], key=sort_key):
            order_map[code] = idx
            idx += 1
    rows = [r[:16] + (order_map.get(r[0], 10 ** 6),) for r in rows]

    c.executemany("INSERT INTO funds(code,name,type,sgzt,shzt,next_open_day,min_buy,daily_limit,"
                  "limit_group,limit_display,fee_flag,buy_code,fee_rate,nav,nav_date,is_bond,sort_order)"
                  " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    c.executemany("INSERT OR REPLACE INTO returns VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", returns_rows)
    c.executemany("INSERT OR REPLACE INTO risk VALUES(?,?,?,?,?,?,?,?)", risk_rows)

    bond_cnt = sum(1 for r in rows if r[15] == 1)
    first_fund_nav_date = next((r[14] for r in rows if r[14]), "")
    meta = {
        "built_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_date": first_fund_nav_date,
        "funds_total": len(rows),
        "db_scope": db_scope,
        "bond_total": bond_cnt,
        "limited_total": len(groups["limited"]),
        "unlimited_total": len(groups["unlimited"]),
        "nodata_total": len(groups["nodata"]),
        "returns_total": len(returns_rows),
        "risk_total": len(risk_rows),
    }
    c.executemany("INSERT OR REPLACE INTO meta VALUES(?,?)", list(meta.items()))
    conn.commit()
    c.execute("VACUUM")
    conn.close()
    print("meta:", meta)
    print(f"DB: {DB} ({os.path.getsize(DB) / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
