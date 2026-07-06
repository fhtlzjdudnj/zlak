#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sooptore(e-ncp) 상품 옵션 API를 호출해서 판매량 데이터를
data/history.json 에 시계열로 누적 저장하는 스크립트.

주의: 이 API는 일반적인 Referer/Origin 외에도 clientid / platform / version
같은 자체 커스텀 헤더를 검사한다. 브라우저 devtools(Network 탭)에서 확인한
값을 HEADERS에 그대로 반영해뒀다.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ---- 설정 -------------------------------------------------------------
PRODUCT_ID = os.environ.get("PRODUCT_ID", "133850457")
API_URL = f"https://shop-api.e-ncp.com/products/{PRODUCT_ID}/options"

# 상품 기본 판매가 (원). 옵션의 addPrice가 이 위에 추가로 더해진다.
BASE_PRICE_KRW = 295000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "ko,en;q=0.9,en-US;q=0.8",
    "Content-Type": "application/json",
    "Referer": "https://sooptore.sooplive.com/",
    "Origin": "https://sooptore.sooplive.com",
    "clientid": "48ZXrkI0gZ+GuBYnWfHPcQ==",
    "platform": "PC",
    "version": "1.0",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_PATH = DATA_DIR / "history.json"
KST = timezone(timedelta(hours=9))


def fetch_raw():
    resp = requests.get(API_URL, headers=HEADERS, params={"preview": ""}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def find_options_list(node):
    if isinstance(node, list):
        if node and isinstance(node[0], dict) and "saleCnt" in node[0]:
            return node
        for item in node:
            found = find_options_list(item)
            if found is not None:
                return found
    elif isinstance(node, dict):
        for v in node.values():
            found = find_options_list(v)
            if found is not None:
                return found
    return None


def extract_sales(raw):
    options = find_options_list(raw) or []

    breakdown = []
    total_sale = 0
    total_stock = 0
    total_amount = 0
    for opt in options:
        sale_cnt = opt.get("saleCnt", 0) or 0
        stock_cnt = opt.get("stockCnt", 0) or 0
        add_price = opt.get("addPrice", 0) or 0
        price = BASE_PRICE_KRW + add_price
        amount = sale_cnt * price
        breakdown.append({
            "optionNo": opt.get("optionNo"),
            "label": opt.get("label"),
            "value": opt.get("value"),
            "saleCnt": sale_cnt,
            "stockCnt": stock_cnt,
            "price": price,
            "amount": amount,
        })
        total_sale += sale_cnt
        total_stock += stock_cnt
        total_amount += amount

    return total_sale, total_stock, total_amount, breakdown


def load_history():
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": []}


def save_history(history):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    now = datetime.now(KST).isoformat()

    try:
        raw = fetch_raw()
    except requests.RequestException as e:
        print(f"[ERROR] API 호출 실패: {e}", file=sys.stderr)
        history = load_history()
        history["records"].append({
            "timestamp": now,
            "error": str(e),
        })
        save_history(history)
        sys.exit(1)

    total_sale, total_stock, total_amount, breakdown = extract_sales(raw)

    history = load_history()
    record = {
        "timestamp": now,
        "sales_value": total_sale,
        "stock_value": total_stock,
        "amount_value": total_amount,
        "options": breakdown,
    }

    history["records"].append(record)

    if not breakdown:
        record["raw_snapshot"] = raw

    save_history(history)

    print(f"[OK] {now} 기록 완료. 총 판매량={total_sale}, 총 판매금액={total_amount}원")


if __name__ == "__main__":
    main()
