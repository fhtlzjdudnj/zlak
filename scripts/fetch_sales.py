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
    # 이 사이트는 아래 커스텀 헤더가 없으면 400을 반환한다 (브라우저 devtools에서 확인)
    "clientid": "48ZXrkI0gZ+GuBYnWfHPcQ==",
    "platform": "PC",
    "version": "1.0",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_PATH = DATA_DIR / "history.json"
KST = timezone(timedelta(hours=9))


def fetch_raw():
    """
    응답은 옵션 객체들의 배열이다. 각 옵션 예시:
    {
      "optionNo": 514748023,
      "label": "상품",
      "value": "일상 ver.세트",
      "addPrice": 0,
      "saleCnt": 430,
      "stockCnt": 9805,
      ...
    }
    """
    resp = requests.get(API_URL, headers=HEADERS, params={"preview": ""}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def extract_sales(raw):
    """
    옵션 배열에서 옵션별 판매량(saleCnt)/재고(stockCnt)를 뽑고,
    전체 합계 판매량을 계산한다.
    """
    options = raw if isinstance(raw, list) else raw.get("options", [])

    breakdown = []
    total_sale = 0
    total_stock = 0
    for opt in options:
        sale_cnt = opt.get("saleCnt", 0) or 0
        stock_cnt = opt.get("stockCnt", 0) or 0
        breakdown.append({
            "optionNo": opt.get("optionNo"),
            "label": opt.get("label"),
            "value": opt.get("value"),
            "saleCnt": sale_cnt,
            "stockCnt": stock_cnt,
        })
        total_sale += sale_cnt
        total_stock += stock_cnt

    return total_sale, total_stock, breakdown


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

    total_sale, total_stock, breakdown = extract_sales(raw)

    history = load_history()
    record = {
        "timestamp": now,
        "sales_value": total_sale,
        "stock_value": total_stock,
        "options": breakdown,
    }

    history["records"].append(record)
    save_history(history)

    print(f"[OK] {now} 기록 완료. 총 판매량={total_sale}, 총 재고={total_stock}")


if __name__ == "__main__":
    main()
