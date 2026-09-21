# -*- coding: utf-8 -*-
"""
东方财富-天天基金网《开放式基金场外申购状态一览表》全量爬虫
页面: https://fund.eastmoney.com/Fund_sgzt.html
接口: https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx?t=8&page={i},50&sort=fcode,asc&js=reData
说明: 与网页端保持一致的分页大小(50条/页), 共 record=27526 条 / pages=551 页
      按 fcode(基金代码) 升序分页, 代码不变, 分页稳定, 避免长爬取过程中限额值变动导致漏抓/重抓
输出: fund_data/raw/page_001.txt ~ page_551.txt  (服务器原始响应, 原样保存)
"""
import json
import os
import re
import sys
import time
import random
import requests


# 目录可被环境变量覆盖 (GitHub Actions 使用), 默认 <repo>/<name>
BASE_DIR = os.environ.get("FUND_DATA_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.environ.get("FUND_RAW_DIR", os.path.join(BASE_DIR, "raw"))
INTER_DIR = os.environ.get("FUND_INTER_DIR", os.path.join(BASE_DIR, "intermediate"))
OUT_DIR = os.environ.get("FUND_OUT_DIR", os.path.join(BASE_DIR, "output"))
os.makedirs(RAW_DIR, exist_ok=True)

API = "https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://fund.eastmoney.com/Fund_sgzt.html",
    "Accept": "*/*",
}
PAGE_SIZE = 50
TOTAL_PAGES = 551

session = requests.Session()
session.headers.update(HEADERS)


def fetch_page(page_idx: int) -> bytes:
    """抓取一页, 返回服务器原始字节; 带重试与退避"""
    url = f"{API}?t=8&page={page_idx},{PAGE_SIZE}&sort=fcode,asc&js=reData"
    last_err = None
    for attempt in range(1, 5):
        try:
            r = session.get(url, timeout=(10, 30))
            r.raise_for_status()
            content = r.content
            # 基本有效性校验
            text_head = content[:200].decode("utf-8", errors="replace")
            if "var reData=" not in text_head or "datas:[" not in text_head:
                raise ValueError(f"响应格式异常: {text_head[:80]!r}")
            return content
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = attempt * 2
            print(f"[page {page_idx}] 第{attempt}次尝试失败: {e}; {wait}s 后重试", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"page {page_idx} 重试 4 次仍失败: {last_err}")


def validate(content: bytes, page_idx: int, expect_pages: int):
    """解析返回的 record/pages/curpage 与本页条数"""
    text = content.decode("utf-8", errors="replace")
    m_rec = re.search(r'record:"(\d+)"', text)
    m_pg = re.search(r'pages:"(\d+)"', text)
    m_cur = re.search(r'curpage:"(\d+)"', text)
    n_items = text.count('["')
    rec = int(m_rec.group(1)) if m_rec else -1
    pages = int(m_pg.group(1)) if m_pg else -1
    cur = int(m_cur.group(1)) if m_cur else -1
    if pages != expect_pages:
        print(f"[page {page_idx}] 警告: pages={pages} 与预期 {expect_pages} 不一致", flush=True)
    if cur != page_idx:
        print(f"[page {page_idx}] 警告: curpage={cur} 与请求页不一致", flush=True)
    return rec, pages, cur, n_items


def main():
    global TOTAL_PAGES  # main 内会按服务端页数动态更新, 必须声明为全局
    start_page = 1
    # 断点续传: 已存在且有效的页文件跳过
    done = set()
    for i in range(1, TOTAL_PAGES + 1):
        fp = os.path.join(RAW_DIR, f"page_{i:03d}.txt")
        if os.path.exists(fp) and os.path.getsize(fp) > 200:
            with open(fp, "rb") as f:
                head = f.read(100).decode("utf-8", errors="replace")
            if "var reData=" in head:
                done.add(i)
    if done:
        print(f"断点续传: 已有 {len(done)} 页缓存", flush=True)

    t0 = time.time()
    total_record = None
    for i in range(1, 10 ** 9):
        if i > TOTAL_PAGES:
            break
        if i in done:
            continue
        content = fetch_page(i)
        fp = os.path.join(RAW_DIR, f"page_{i:03d}.txt")
        with open(fp, "wb") as f:
            f.write(content)
        rec, pages, cur, n_items = validate(content, i, TOTAL_PAGES)
        if pages > 0 and pages != TOTAL_PAGES:
            print(f"服务端页数变化: {TOTAL_PAGES} -> {pages}, 自动跟随", flush=True)
            TOTAL_PAGES = pages
        if total_record is None:
            total_record = rec
        if i % 25 == 0 or i == TOTAL_PAGES:
            elapsed = time.time() - t0
            eta = elapsed / i * (TOTAL_PAGES - i)
            print(f"进度 {i}/{TOTAL_PAGES} 页 | 本页{n_items}条 | 总记录{rec} | "
                  f"已用{elapsed:.0f}s 剩余约{eta:.0f}s", flush=True)
        time.sleep(0.15 + random.random() * 0.15)  # 限速, 对站点友好

    print(f"抓取完成: 共 {TOTAL_PAGES} 页, 总记录 {total_record} 条, "
          f"耗时 {time.time() - t0:.0f}s", flush=True)

    # 抓取完整性校验: 每页条数 + 汇总条数
    total_items = 0
    bad_pages = []
    p1_text = open(os.path.join(RAW_DIR, "page_001.txt"), "rb").read().decode("utf-8", errors="replace")
    m1 = re.search(r'record:"(\d+)"', p1_text)
    total_record = int(m1.group(1)) if m1 else None
    for i in range(1, TOTAL_PAGES + 1):
        fp = os.path.join(RAW_DIR, f"page_{i:03d}.txt")
        text = open(fp, "rb").read().decode("utf-8", errors="replace")
        m = re.search(r"datas:(\[.*?\]),record:", text, re.S)
        if not m:
            bad_pages.append((i, "no datas"))
            continue
        try:
            arr = json.loads(m.group(1))
        except Exception as e:  # noqa: BLE001
            bad_pages.append((i, f"json err: {e}"))
            continue
        expect = PAGE_SIZE if i < TOTAL_PAGES else total_record - PAGE_SIZE * (TOTAL_PAGES - 1)
        if len(arr) != expect:
            bad_pages.append((i, f"items={len(arr)} expect={expect}"))
        total_items += len(arr)
    print(f"汇总: 全部页累计 {total_items} 条", flush=True)
    if bad_pages:
        print("异常页:", bad_pages, flush=True)
        sys.exit(2)
    print("完整性校验通过: 无缺页/缺条", flush=True)


if __name__ == "__main__":
    main()
