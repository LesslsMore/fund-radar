# -*- coding: utf-8 -*-
"""
批量获取基金风险指标(夏普比率/标准差, 近1年/近2年/近3年)

数据源: 天天基金 F10 特色数据页(服务端直出, 无JSON批量接口, 逐只抓取)
  https://fundf10.eastmoney.com/tsdata_{code}.html
页面内风险指标表格(已用 006431 汇安鼎利纯债A 验证):
  <th>近1年</th><th>近2年</th><th>近3年</th>
  <tr><td>标准差</td><td>0.43%</td>...</tr>
  <tr><td>夏普比率</td><td>7.26</td>...</tr>
  <div class="limit-time">截止至：2026-09-11</div>

输出: intermediate/sharpe_parsed.json + 合并进两个 *_含收益率.csv 最终表
"""
import json
import os
import re
import csv
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


# 目录可被环境变量覆盖 (GitHub Actions 使用), 默认 <repo>/<name>
BASE_DIR = os.environ.get("FUND_DATA_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.environ.get("FUND_RAW_DIR", os.path.join(BASE_DIR, "raw"))
INTER_DIR = os.environ.get("FUND_INTER_DIR", os.path.join(BASE_DIR, "intermediate"))
OUT_DIR = os.environ.get("FUND_OUT_DIR", os.path.join(BASE_DIR, "output"))
os.makedirs(RAW_DIR, exist_ok=True)

URL = "https://fundf10.eastmoney.com/tsdata_{}.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://fund.eastmoney.com/",
}
PERIODS = ["近1年", "近2年", "近3年"]
SHARPE_FIELDS = (["标准差_" + p + "%" for p in PERIODS]
                 + ["夏普比率_" + p for p in PERIODS] + ["风险指标截止日"])

session = requests.Session()
session.headers.update(HEADERS)


def fetch_one(code: str):
    """抓单只 tsdata 页并解析, 返回 (code, dict)"""
    fp = os.path.join(RAW_DIR, f"{code}.html")
    text = None
    if os.path.exists(fp) and os.path.getsize(fp) > 2000:
        text = open(fp, "rb").read().decode("utf-8", errors="replace")
    if text is None:
        for attempt in range(1, 4):
            try:
                r = session.get(URL.format(code), timeout=(10, 30))
                r.raise_for_status()
                if "标准差" not in r.text:
                    raise ValueError("页面无标准差(可能未生成)")
                open(fp, "wb").write(r.content)
                text = r.text
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    return code, {"_status": f"抓取失败: {e}"}
                time.sleep(attempt * 2)
        time.sleep(0.05 + random.random() * 0.1)
    try:
        return code, parse_tsdata(text)
    except Exception as e:  # noqa: BLE001
        return code, {"_status": f"解析失败: {e}"}


def parse_tsdata(txt: str) -> dict:
    i = txt.find("标准差")
    if i < 0:
        return {"_status": "无风险指标数据"}
    win = txt[max(0, i - 1500): i + 800]
    # 表头: 确认列顺序
    ths = [t for t in re.findall(r"<th[^>]*>([^<]*)</th>", win) if t.strip()]
    periods = [t for t in ths if t in PERIODS]
    if periods != PERIODS:
        return {"_status": f"表头异常: {periods}"}
    out = {}
    m_deadline = re.search(r"截止至[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", win)
    out["风险指标截止日"] = m_deadline.group(1) if m_deadline else ""
    for label, prefix in [("标准差", "标准差"), ("夏普比率", "夏普比率")]:
        m = re.search(r"<tr><td>" + label + r"</td>(.*?)</tr>", win, re.S)
        if not m:
            for p in PERIODS:
                out[f"{prefix}_{p}" + ("%" if label == "标准差" else "")] = ""
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(1))
        for j, p in enumerate(PERIODS):
            v = cells[j].strip() if j < len(cells) else ""
            key = f"{prefix}_{p}" + ("%" if label == "标准差" else "")
            out[key] = "" if v in ("--", "-", "&nbsp;") else v
    out["_status"] = "ok"
    return out


def safe_write_csv(path, fieldnames, rows):
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        return path
    except PermissionError:
        alt = path.replace(".csv", "_v2.csv")
        with open(alt, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"警告: {path} 被占用, 已改存为 {alt}", flush=True)
        return alt


def main():
    with open(os.path.join(OUT_DIR, "债券型基金_有限额_按限额升序.csv"), encoding="utf-8-sig") as f:
        base = list(csv.DictReader(f))
    codes = [r["基金代码"] for r in base]
    print(f"目标基金: {len(codes)} 只", flush=True)

    cache_fp = os.path.join(INTER_DIR, "sharpe_parsed.json")
    parsed = {}
    if os.path.exists(cache_fp):
        parsed = json.load(open(cache_fp, encoding="utf-8"))
        print(f"缓存已有 {len(parsed)} 只", flush=True)
    todo = [c for c in codes if c not in parsed]
    print(f"需抓取 {len(todo)} 只", flush=True)

    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(fetch_one, c) for c in todo]
        for fu in as_completed(futs):
            code, d = fu.result()
            parsed[code] = d
            done += 1
            if done % 100 == 0:
                print(f"进度 {done}/{len(todo)}, {time.time()-t0:.0f}s", flush=True)
    json.dump(parsed, open(cache_fp, "w", encoding="utf-8"), ensure_ascii=False)
    ok = sum(1 for v in parsed.values() if v.get("_status") == "ok")
    print(f"抓取+解析完成: ok {ok}/{len(codes)}, {time.time()-t0:.0f}s", flush=True)
    bad = {c: v.get("_status") for c, v in parsed.items() if v.get("_status") != "ok"}
    if bad:
        print("异常:", dict(list(bad.items())[:10]), flush=True)

    # 合并进最终表(以含收益率版本为基础, 同步刷新无后缀版本)
    for fname in ["债券型基金_有限额_按限额升序_含收益率.csv",
                  "债券型基金_限大额可买_按限额升序_含收益率.csv",
                  "债券型基金_有限额_按限额升序.csv",
                  "债券型基金_限大额可买_按限额升序.csv"]:
        fp = os.path.join(OUT_DIR, fname)
        if not os.path.exists(fp):
            print(f"跳过(不存在): {fname}")
            continue
        with open(fp, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            d = parsed.get(r["基金代码"], {})
            for fld in SHARPE_FIELDS:
                r[fld] = d.get(fld, "") if d.get("_status") == "ok" else ""
            if d.get("_status") not in ("ok",):
                r["夏普比率_近1年"] = r.get("夏普比率_近1年", "")
        fieldnames = list(rows[0].keys())
        out = safe_write_csv(fp, fieldnames, rows)
        n_sp = sum(1 for r in rows if r.get("夏普比率_近1年"))
        print(f"已写 {out} | 近1年夏普有值 {n_sp}/{len(rows)}")

    # 摘要
    vals = [(c, v["夏普比率_近1年"]) for c, v in parsed.items()
            if v.get("_status") == "ok" and v["夏普比率_近1年"]]
    fv = sorted(((float(s), c) for c, s in vals), reverse=True)
    print(f"\n近1年夏普分布: n={len(fv)}, 最高 {fv[0]}, 最低 {fv[-1]}")
    print("006431 解析结果:", parsed.get("006431"))


if __name__ == "__main__":
    main()
