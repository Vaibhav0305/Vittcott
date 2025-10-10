"""Non-destructive smoke test for Vittcott backend.

This script performs two safe checks against a running backend:
  1) POST /ai/ask with a short, harmless prompt
  2) GET /api/finance/quote for a known ticker (MSFT)

It measures and prints latencies and short response summaries. Exit code is 0 when both checks return HTTP 200, else non-zero.

Usage:
  (from project root)\n  backend\.venv\Scripts\python.exe backend\scripts\smoke_test.py

Environment variables:
  VITTCOTT_BACKEND_URL - override the default backend URL (default http://localhost:8000)
"""

import os
import sys
import time
import json
from typing import Tuple

try:
    import requests
except Exception:
    print("The 'requests' library is required. Install it in your venv: pip install requests")
    sys.exit(2)


def measure_post(url: str, json_body: dict, timeout: int = 30) -> Tuple[int, float, dict]:
    t0 = time.perf_counter()
    r = requests.post(url, json=json_body, timeout=timeout)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000.0
    try:
        data = r.json()
    except Exception:
        data = {"text": r.text}
    return r.status_code, elapsed, data


def measure_get(url: str, params: dict = None, timeout: int = 30) -> Tuple[int, float, dict]:
    t0 = time.perf_counter()
    r = requests.get(url, params=params, timeout=timeout)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000.0
    try:
        data = r.json()
    except Exception:
        data = {"text": r.text}
    return r.status_code, elapsed, data


def summarize_text(s: str, maxlen: int = 300) -> str:
    s = s.replace("\n", " ")
    if len(s) > maxlen:
        return s[:maxlen] + "..."
    return s


def main():
    backend_url = os.getenv("VITTCOTT_BACKEND_URL", "http://localhost:8000").rstrip("/")
    print(f"Using backend: {backend_url}")

    ai_url = f"{backend_url}/api/ai/ask"
    finance_url = f"{backend_url}/api/finance/quote"

    ok = True

    print("\n1) AI smoke test: POST /ai/ask (minimal prompt)")
    body = {"query": "Say hello briefly", "portfolio": {}}
    try:
        status, elapsed_ms, data = measure_post(ai_url, body, timeout=60)
        print(f"  Status: {status}, latency: {elapsed_ms:.0f} ms")
        if status == 200:
            text = data.get("response_text") if isinstance(data, dict) else None
            if text:
                print("  Response (truncated):", summarize_text(text))
            else:
                print("  Response JSON:", json.dumps(data)[:400])
        else:
            print("  Error response:", summarize_text(json.dumps(data)))
            ok = False
    except Exception as e:
        print("  Failed to call AI endpoint:", str(e))
        ok = False

    print("\n2) Finance smoke test: GET /api/finance/quote?symbol=MSFT")
    try:
        status, elapsed_ms, data = measure_get(finance_url, params={"symbol": "MSFT"}, timeout=30)
        print(f"  Status: {status}, latency: {elapsed_ms:.0f} ms")
        if status == 200:
            # show price + number of candles
            price = data.get("price")
            candles = data.get("candles") or []
            print(f"  Price: {price}")
            print(f"  Candles returned: {len(candles)} (showing up to 3)" )
            for c in (candles[:3] if isinstance(candles, list) else []):
                ts = c.get("ts")
                close = c.get("close")
                print(f"    {ts} close={close}")
        else:
            print("  Error response:", summarize_text(json.dumps(data)))
            ok = False
    except Exception as e:
        print("  Failed to call finance endpoint:", str(e))
        ok = False

    print("\nSummary:")
    if ok:
        print("  ✅ All smoke tests passed")
        sys.exit(0)
    else:
        print("  ❌ One or more checks failed")
        sys.exit(3)


if __name__ == "__main__":
    main()
