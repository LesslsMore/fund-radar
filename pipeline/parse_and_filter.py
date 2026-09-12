# -*- coding: utf-8 -*-
"""
解析 raw/ 下 551 页原始数据 -> 中间数据 -> 筛选 -> 最终排序结果

字段映射 (来自页面 sgzt_new_js.js 的 CreateRowContent):
  d[0] 基金代码       d[1] 基金简称       d[2] 基金类型
  d[3] 最新净值/万份收益  d[4] 净值日期      d[5] 申购状态   d[6] 赎回状态
  d[7] 下一开放日      d[8] 购买起点(minsg)  d[9] 日累计限定金额(maxsg)
  d[10] 费率标志       d[11] 申购状态代码    d[12] 手续费率

网页端展示规则 (MoneyChange / IsSuspended):
  - 申购状态代码不在 1~10 -> 显示 "---"
  - 限额 >= 8亿(800000000) -> 显示 "无限额"  (实际数据里无限额基金多为 1000亿 哨兵值)
  - 限额 < 0               -> 显示 "---"
  - 其余                    -> 显示具体限额
因此 "有限额" 定义 = 申购状态代码在 1~10 且 0 <= 限额 < 8亿
"""
import json
import os
import re
import csv
from collections import Counter


# 目录可被环境变量覆盖 (GitHub Actions 使用), 默认 <repo>/<name>
BASE_DIR = os.environ.get("FUND_DATA_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.environ.get("FUND_RAW_DIR", os.path.join(BASE_DIR, "raw"))
INTER_DIR = os.environ.get("FUND_INTER_DIR", os.path.join(BASE_DIR, "intermediate"))
OUT_DIR = os.environ.get("FUND_OUT_DIR", os.path.join(BASE_DIR, "output"))
os.makedirs(INTER_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

PAGE_SIZE = 50

def _detect_pages():
    import glob
    files = glob.glob(os.path.join(RAW_DIR, "page_*.txt"))
    ns = [int(re.search(r"(\d+)\.txt$", f).group(1)) for f in files if re.search(r"(\d+)\.txt$", f)]
    return max(ns) if ns else 551

TOTAL_PAGES = _detect_pages()
BUYABLE_CODES = {str(i) for i in range(1, 11)}
UNLIMITED_THRESHOLD = 8 * 1e8  # 网页端 >=8亿 显示"无限额"


def fmt_limit(v: float) -> str:
    """人类可读的限额展示(元/万/亿)"""
    if v < 1e4:
        return f"{v:g}元"
    if v < 1e8:
        return f"{v / 1e4:g}万"
    return f"{v / 1e8:g}亿"


def parse_all_pages():
    funds = []
    for i in range(1, TOTAL_PAGES + 1):
        fp = os.path.join(RAW_DIR, f"page_{i:03d}.txt")
        text = open(fp, "rb").read().decode("utf-8", errors="replace")
        m = re.search(r"datas:(\[.*?\]),record:", text, re.S)
        if not m:
            raise RuntimeError(f"page_{i:03d}.txt 无法解析 datas")
        for d in json.loads(m.group(1)):
            try:
                daily_limit = float(d[9])
            except (TypeError, ValueError):
                daily_limit = -1.0
            try:
                min_buy = float(d[8])
            except (TypeError, ValueError):
                min_buy = -1.0
            buy_code = str(d[11]).strip()
            buyable = buy_code in BUYABLE_CODES
            site_shows_limit = buyable and (0 <= daily_limit < UNLIMITED_THRESHOLD)
            funds.append({
                "基金代码": d[0],
                "基金简称": d[1],
                "基金类型": d[2],
                "最新净值": d[3],
                "净值日期": d[4],
                "申购状态": d[5],
                "赎回状态": d[6],
                "下一开放日": d[7],
                "购买起点_元": min_buy,
                "日累计申购限额_元": daily_limit,
                "费率标志": d[10],
                "申购状态代码": d[11],
                "手续费率": d[12],
                "限额展示": fmt_limit(daily_limit) if site_shows_limit else "",
                "有限额": site_shows_limit,
                "债券型": "债券" in d[2],
            })
    return funds


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


ALL_FIELDS = ["基金代码", "基金简称", "基金类型", "最新净值", "净值日期", "申购状态",
              "赎回状态", "下一开放日", "购买起点_元", "日累计申购限额_元", "费率标志",
              "申购状态代码", "手续费率", "限额展示", "有限额", "债券型"]
FINAL_FIELDS = ["序号", "基金代码", "基金简称", "基金类型", "申购状态", "赎回状态",
                "日累计申购限额_元", "限额展示", "购买起点_元", "手续费率",
                "最新净值", "净值日期", "下一开放日", "基金链接"]


def main():
    funds = parse_all_pages()
    print(f"解析完成: {len(funds)} 条基金记录")
    codes = [f["基金代码"] for f in funds]
    dup = [c for c, n in Counter(codes).items() if n > 1]
    print(f"重复基金代码: {len(dup)} 个" + (f" -> {dup[:10]}" if dup else ""))

    # 中间数据 1: 全量
    write_csv(os.path.join(INTER_DIR, "all_funds.csv"), funds, ALL_FIELDS)
    with open(os.path.join(INTER_DIR, "all_funds.json"), "w", encoding="utf-8") as f:
        json.dump(funds, f, ensure_ascii=False)

    # 中间数据 2: 债券型
    bonds = [f for f in funds if f["债券型"]]
    write_csv(os.path.join(INTER_DIR, "bond_funds.csv"), bonds, ALL_FIELDS)
    print(f"债券型基金: {len(bonds)} 只")
    print("  类型分布:", dict(Counter(f["基金类型"] for f in bonds)))
    print("  申购状态分布:", dict(Counter(f["申购状态"] for f in bonds)))

    # 中间数据 3: 债券型 且 有限额
    bond_limit = [f for f in bonds if f["有限额"]]
    write_csv(os.path.join(INTER_DIR, "bond_funds_with_limit.csv"), bond_limit, ALL_FIELDS)
    print(f"债券型且有限额: {len(bond_limit)} 只")
    print("  申购状态分布:", dict(Counter(f["申购状态"] for f in bond_limit)))

    # 限额=0 的边界情况
    zero_limit = [f for f in bond_limit if f["日累计申购限额_元"] == 0]
    print(f"  其中限额为 0 元的: {len(zero_limit)} 只"
          + (f" 例: {[f['基金代码'] for f in zero_limit[:5]]}" if zero_limit else ""))

    # 最终输出 1: 数据口径——债券型 且 有限额(站点会展示限额值), 按限额从小到大排序
    bond_limit.sort(key=lambda x: (x["日累计申购限额_元"], x["基金代码"]))

    def to_final_rows(rows):
        final = []
        for idx, f in enumerate(rows, 1):
            raw = f["日累计申购限额_元"]
            final.append({
                "序号": idx,
                "基金代码": f["基金代码"],
                "基金简称": f["基金简称"],
                "基金类型": f["基金类型"],
                "申购状态": f["申购状态"],
                "赎回状态": f["赎回状态"],
                "日累计申购限额_元": int(raw) if raw == int(raw) else raw,
                "限额展示": f["限额展示"],
                "购买起点_元": int(f["购买起点_元"]) if f["购买起点_元"] == int(f["购买起点_元"]) else f["购买起点_元"],
                "手续费率": f["手续费率"],
                "最新净值": f["最新净值"],
                "净值日期": f["净值日期"],
                "下一开放日": f["下一开放日"],
                "基金链接": f"http://fund.eastmoney.com/{f['基金代码']}.html",
            })
        return final

    out_path = os.path.join(OUT_DIR, "债券型基金_有限额_按限额升序.csv")
    final_rows = to_final_rows(bond_limit)
    write_csv(out_path, final_rows, FINAL_FIELDS)
    print(f"最终结果(数据口径, 含暂停申购/封闭期)已写入: {out_path} ({len(final_rows)} 行)")

    # 最终输出 2: 实操口径——仅"限大额"(当前可买、且单日申购有上限), 按限额从小到大排序
    bond_limit_buyable = [f for f in bond_limit if f["申购状态"] == "限大额"]
    out_path2 = os.path.join(OUT_DIR, "债券型基金_限大额可买_按限额升序.csv")
    final_rows2 = to_final_rows(bond_limit_buyable)
    write_csv(out_path2, final_rows2, FINAL_FIELDS)
    print(f"最终结果(限大额, 当前可买)已写入: {out_path2} ({len(final_rows2)} 行)")

    print("\n限额最小的前 10 只(数据口径):")
    for r in final_rows[:10]:
        print(f"  {r['基金代码']} {r['基金简称']} | {r['基金类型']} | {r['申购状态']} | "
              f"限额 {r['限额展示']} ({r['日累计申购限额_元']}元)")
    print("\n[限大额可买口径] 限额最小的前 10 只:")
    for r in final_rows2[:10]:
        print(f"  {r['基金代码']} {r['基金简称']} | {r['基金类型']} | "
              f"限额 {r['限额展示']} ({r['日累计申购限额_元']}元)")
    print("\n限额最大的后 5 只:")
    for r in final_rows[-5:]:
        print(f"  {r['基金代码']} {r['基金简称']} | {r['限额展示']} ({r['日累计申购限额_元']}元)")


if __name__ == "__main__":
    main()
