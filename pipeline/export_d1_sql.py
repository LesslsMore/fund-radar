# -*- coding: utf-8 -*-
"""
把 api/db/funds.db 导出为 D1 可执行的 SQL (d1_dump.sql), 供 wrangler 导入:
    wrangler d1 execute fund-radar --remote --file=pipeline/data/d1_dump.sql   # 远端
    wrangler d1 execute fund-radar --local  --file=pipeline/data/d1_dump.sql   # 本地开发
注意: D1 不支持 BEGIN/COMMIT 脚本, 每 200 行合成一条多值 INSERT 控制语句大小。
"""
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("FUND_DB_PATH", os.path.join(BASE, "api", "db", "funds.db"))
OUT = os.environ.get("D1_DUMP_PATH", os.path.join(BASE, "pipeline", "data", "d1_dump.sql"))
MAX_MB = float(os.environ.get("D1_CHUNK_MB", "4"))
BATCH = 200


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def rows(c, table, cols):
    return c.execute(f"SELECT {','.join(cols)} FROM {table}").fetchall()


def insert_statements(c, table, cols, rows, replace=False):
    head = (f"INSERT OR REPLACE INTO {table}({','.join(cols)}) VALUES " if replace
            else f"DELETE FROM {table};\nINSERT INTO {table}({','.join(cols)}) VALUES ")
    out = []
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        values = ",".join("(" + ",".join(lit(v) for v in r) + ")" for r in chunk)
        if i == 0:
            out.append(head + values + ";")
        else:
            out.append(f"INSERT INTO {table}({','.join(cols)}) VALUES {values};")
    return out


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 1. 建表 DDL (从源库 sqlite_master 提取, 改为 IF NOT EXISTS 以支持重复导入)
    ddl = []
    for (sql,) in c.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
    ).fetchall():
        s = re.sub(r"\bCREATE\s+TABLE\b", "CREATE TABLE IF NOT EXISTS", sql, flags=re.I)
        s = re.sub(r"\bCREATE\s+(UNIQUE\s+)?INDEX\b",
                   lambda m: f"CREATE {m.group(1) or ''}INDEX IF NOT EXISTS", s, flags=re.I)
        ddl.append(s.rstrip(";") + ";")
    stmts = ddl + ["DELETE FROM funds;", "DELETE FROM returns;", "DELETE FROM risk;", "DELETE FROM meta;"]
    stmts += insert_statements(c, "funds",
        ["code", "name", "type", "sgzt", "shzt", "next_open_day", "min_buy", "daily_limit",
         "limit_group", "limit_display", "fee_flag", "buy_code", "fee_rate", "nav", "nav_date",
         "is_bond", "sort_order"], rows(c, "funds", ["code", "name", "type", "sgzt", "shzt",
         "next_open_day", "min_buy", "daily_limit", "limit_group", "limit_display", "fee_flag",
         "buy_code", "fee_rate", "nav", "nav_date", "is_bond", "sort_order"]))
    stmts += insert_statements(c, "returns",
        ["code", "w", "m1", "m3", "m6", "y1", "y2", "y3", "ytd", "since", "source", "nav_date2"],
        rows(c, "returns", ["code", "w", "m1", "m3", "m6", "y1", "y2", "y3", "ytd", "since",
                            "source", "nav_date2"]))
    stmts += insert_statements(c, "risk",
        ["code", "std_1y", "std_2y", "std_3y", "sharpe_1y", "sharpe_2y", "sharpe_3y", "as_of"],
        rows(c, "risk", ["code", "std_1y", "std_2y", "std_3y", "sharpe_1y", "sharpe_2y",
                         "sharpe_3y", "as_of"]))
    stmts += insert_statements(c, "meta", ["key", "value"],
        rows(c, "meta", ["key", "value"]), replace=True)
    conn.close()

    # 分片: 每片 <= MAX_MB (规避 D1 单次执行大小限制); 顺序执行片即完整导入
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base = OUT.replace(".sql", "")
    chunks, cur, size = [], [], 0
    for s in stmts:
        cur.append(s)
        size += len(s.encode("utf-8"))
        if size >= MAX_MB * 1024 * 1024:
            chunks.append(cur); cur, size = [], 0
    if cur:
        chunks.append(cur)
    paths = []
    for i, ch in enumerate(chunks):
        p = f"{base}_{i:02d}.sql"
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(ch))
        paths.append(p)
    # 清理旧分片 (防止上一轮更多分片残留)
    import glob
    for old in glob.glob(base + "_*.sql"):
        if old not in paths:
            os.remove(old)
    print(f"导出 {len(stmts)} 条语句 -> {len(paths)} 个分片: {paths[0]} ... 共 "
          f"{sum(os.path.getsize(p) for p in paths)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
