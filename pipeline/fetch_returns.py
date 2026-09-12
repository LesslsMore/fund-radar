# -*- coding: utf-8 -*-
"""
批量获取基金阶段涨幅(近1周~成立来, 含近1年), 合并进两个最终结果表

数据源 1 (批量, 主): 基金排行接口, 每页 200 条共 102 页, 覆盖 20334 只
  https://fund.eastmoney.com/data/rankhandler.aspx?op=ph&dt=kf&ft=all&rs=&gs=0
    &sc=1nzf&st=desc&sd=2025-09-12&ed=2026-09-12&qdii=&tabSubtype=,,,,,&pi={i}&pn=200&dx=1
  记录字段(逗号分隔, 0起):
  0代码 1简称 2拼音 3净值日期 4单位净值 5累计净值 6日增长率 7近1周 8近1月 9近3月
  10近6月 11近1年 12近2年 13近3年 14今年来 15成立来 16成立日期 17~ 基金公司/手续费等

数据源 2 (单只, 补漏): https://fund.eastmoney.com/pingzhongdata/{code}.js
  变量 syl_1y=近1月 syl_3y=近3月 syl_6y=近6月 syl_1n=近1年  (与详情页数字一致, 已用 016664=79.38 验证)

已验证的字段锚点: 016664 -> 近1月3.19 近3月-13.03 近6月28.44 近1年79.38 (两个数据源一致)
"""
import json
import os
import re
import csv
import time
import random
import requests


# 目录可被环境变量覆盖 (GitHub Actions 使用), 默认 <repo>/<name>
BASE_DIR = os.environ.get("FUND_DATA_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.environ.get("FUND_RAW_DIR", os.path.join(BASE_DIR, "raw"))
INTER_DIR = os.environ.get("FUND_INTER_DIR", os.path.join(BASE_DIR, "intermediate"))
OUT_DIR = os.environ.get("FUND_OUT_DIR", os.path.join(BASE_DIR, "output"))

RANK_URL = ("https://fund.eastmoney.com/data/rankhandler.aspx?op=ph&dt=kf&ft=all&rs=&gs=0"
            "&sc=1nzf&st=desc&sd=2025-09-12&ed=2026-09-12&qdii=&tabSubtype=,,,,,&pi={pi}&pn=200&dx=1")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://fund.eastmoney.com/data/fundranking.html",
}
PN = 200
RET_FIELDS = ["近1周", "近1月", "近3月", "近6月", "近1年", "近2年", "近3年", "今年来", "成立来"]

session = requests.Session()
session.headers.update(HEADERS)


def fetch_rank_pages():
    """抓取排行接口全部页, 保存原始响应, 返回 {code: 字段dict}"""
    ranks = {}
    pi = 1
    all_records = None
    t0 = time.time()
    while True:
        fp = os.path.join(RAW_DIR, f"rank_1nzf_p{pi}.txt")
        if os.path.exists(fp) and os.path.getsize(fp) > 500:
            text = open(fp, "rb").read().decode("utf-8", errors="replace")
        else:
            for attempt in range(1, 5):
                try:
                    r = session.get(RANK_URL.format(pi=pi), timeout=(10, 30))
                    r.raise_for_status()
                    if "var rankData" not in r.text[:50]:
                        raise ValueError(f"格式异常: {r.text[:60]!r}")
                    open(fp, "wb").write(r.content)
                    text = r.text
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"[rank p{pi}] 第{attempt}次失败: {e}", flush=True)
                    time.sleep(attempt * 2)
            else:
                raise RuntimeError(f"rank p{pi} 重试后仍失败")
        m = re.search(r'"(\d{6},[^"]*)"', text)
        if not m:
            raise RuntimeError(f"rank p{pi} 无数据")
        recs = re.findall(r'"(\d{6},[^"]*)"', text)
        meta = re.search(r"allRecords:(\d+),pageIndex:(\d+),pageNum:(\d+),allPages:(\d+)", text)
        all_records = int(meta.group(1))
        all_pages = int(meta.group(4))
        for rec in recs:
            f = rec.split(",")
            ranks[f[0]] = {
                "净值日期": f[3], "单位净值": f[4], "累计净值": f[5], "日增长率": f[6],
                "近1周": f[7], "近1月": f[8], "近3月": f[9], "近6月": f[10],
                "近1年": f[11], "近2年": f[12], "近3年": f[13], "今年来": f[14],
                "成立来": f[15], "成立日期": f[16] if len(f) > 16 else "",
            }
        if pi % 10 == 0 or pi == all_pages:
            print(f"rank 进度 {pi}/{all_pages} 页, 累计 {len(ranks)} 只, {time.time()-t0:.0f}s", flush=True)
        if pi >= all_pages:
            break
        pi += 1
        time.sleep(0.15 + random.random() * 0.15)
    print(f"rank 抓取完成: {len(ranks)} 只 (接口 allRecords={all_records}), {time.time()-t0:.0f}s", flush=True)
    return ranks


def fetch_pingzhong(code: str):
    """单只补漏: pingzhongdata JS -> 阶段涨幅"""
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    for attempt in range(1, 4):
        try:
            r = session.get(url, timeout=(10, 30),
                            headers={"Referer": f"https://fund.eastmoney.com/{code}.html"})
            r.raise_for_status()
            text = r.text

            def sv(name):
                m = re.search(name + r'="([^"]*)"', text)
                return m.group(1) if m else ""
            return {"近1月": sv("syl_1y"), "近3月": sv("syl_3y"),
                    "近6月": sv("syl_6y"), "近1年": sv("syl_1n"),
                    "近1周": "", "近2年": "", "近3年": "", "今年来": "", "成立来": ""}
        except Exception as e:  # noqa: BLE001
            print(f"[pingzhong {code}] 第{attempt}次失败: {e}", flush=True)
            time.sleep(attempt * 2)
    return None


def safe_write_csv(path, fieldnames, rows):
    """目标文件被占用(如在Excel中打开)时, 自动改存为 *_含收益率.csv"""
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        return path
    except PermissionError:
        alt = path.replace(".csv", "_含收益率.csv")
        with open(alt, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"警告: {path} 被占用(可能正被Excel打开), 已改存为 {alt}", flush=True)
        return alt


def main():
    ranks = fetch_rank_pages()

    # 读入此前两个最终结果
    finals = {}
    for key, fname in [("data口径", "债券型基金_有限额_按限额升序.csv"),
                       ("限大额", "债券型基金_限大额可买_按限额升序.csv")]:
        with open(os.path.join(OUT_DIR, fname), encoding="utf-8-sig") as f:
            finals[key] = list(csv.DictReader(f))
        print(f"读入 {key}: {len(finals[key])} 行")

    # 覆盖率检查 + 补漏 (结果缓存到 JSON, 重跑免重复请求)
    patch_cache = os.path.join(INTER_DIR, "patched_returns.json")
    target_codes = {r["基金代码"] for r in finals["data口径"]}
    missing = sorted(target_codes - set(ranks))
    print(f"目标 {len(target_codes)} 只中, rank 接口覆盖 {len(target_codes) - len(missing)} 只, 缺 {len(missing)} 只")
    patched = {}
    if os.path.exists(patch_cache):
        patched = json.load(open(patch_cache, encoding="utf-8"))
        print(f"使用补漏缓存: {len(patched)} 只")
    need = [c for c in missing if c not in patched]
    for i, code in enumerate(need, 1):
        d = fetch_pingzhong(code)
        patched[code] = d if d is not None else {}
        if d is not None and i <= 5:
            print(f"  补漏 {code}: 近1年={d['近1年']!r}")
        time.sleep(0.2 + random.random() * 0.2)
    if need:
        json.dump(patched, open(patch_cache, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"pingzhongdata 补漏完成: 成功 {sum(1 for v in patched.values() if v)} / {len(patched)}")

    # 交叉验证: 两个数据源都有的基金, 随机抽 15 只对比近1年
    import itertools
    common = list(target_codes & set(ranks))
    random.seed(42)
    sample = random.sample(common, min(15, len(common)))
    bad = 0
    for code in sample:
        pz = fetch_pingzhong(code)
        if pz is None:
            continue
        a, b = ranks[code]["近1年"], pz["近1年"]
        fa = float(a) if a not in ("", "--") else None
        fb = float(b) if b not in ("", "--") else None
        if (fa is None) != (fb is None) or (fa is not None and abs(fa - fb) > 0.005):
            print(f"  交叉验证不一致 {code}: rank={a!r} pingzhong={b!r}")
            bad += 1
        time.sleep(0.15)
    print(f"交叉验证: 抽样 {len(sample)} 只, 不一致 {bad} 只")

    # 中间数据: 全部 rank 基金的阶段涨幅表
    rank_rows = [{"基金代码": c, **v, "数据来源": "rank"} for c, v in ranks.items()]
    with open(os.path.join(INTER_DIR, "rank_all_funds_returns.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["基金代码", *RET_FIELDS, "净值日期", "单位净值",
                                          "累计净值", "日增长率", "成立日期", "数据来源"])
        w.writeheader()
        w.writerows(rank_rows)

    # 合并进两个最终结果 (保持原排序, 追加阶段涨幅列)
    for key in finals:
        rows = finals[key]
        for r in rows:
            code = r["基金代码"]
            src = ""
            if code in ranks:
                v, src = ranks[code], "rank"
            elif code in patched and patched[code]:
                v, src = patched[code], "pingzhongdata"
            else:
                v, src = {}, ""
            for fld in RET_FIELDS:
                r[fld + "_收益率%"] = v.get(fld, "")
            r["收益数据来源"] = src if v else "无数据"
        fieldnames = list(rows[0].keys())
        out = safe_write_csv(os.path.join(OUT_DIR, finals_name(key)), fieldnames, rows)
        n_with = sum(1 for r in rows if r["近1年_收益率%"] != "")
        print(f"{key}: 已写 {out} | 近1年有值 {n_with}/{len(rows)}")


def finals_name(key):
    return ("债券型基金_有限额_按限额升序.csv" if key == "data口径"
            else "债券型基金_限大额可买_按限额升序.csv")


if __name__ == "__main__":
    main()
