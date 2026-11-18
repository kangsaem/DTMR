"""종목 하나의 리포트 계산 근거를 덤프(머니파이 앱과 판정 비교용, 2026-11-19). python dbg_bars.py OXY → results/dbg_OXY.json"""
import json, sys
import market_report as M

code = sys.argv[1] if len(sys.argv) > 1 else "OXY"
df = M.load_prices(code)
r = M.analyze(code, code)
c = df["Close"].dropna()
out = {
    "code": code,
    "bars": {"dates": [f"{d:%Y-%m-%d}" for d in df.index], "close": [None if v != v else float(v) for v in df["Close"]],
             "high": [None if v != v else float(v) for v in df["High"]] if "High" in df else None,
             "low": [None if v != v else float(v) for v in df["Low"]] if "Low" in df else None},
    "last": f"{c.index[-1]:%Y-%m-%d}", "close": float(c.iloc[-1]),
    "rsi": r.get("rsi"), "sig": {k: v for k, v in (r.get("sig") or {}).items()},
    "month": r.get("month"), "week": r.get("week"), "day": r.get("day"),
    "bottom": r.get("bottom"), "bottom_near": r.get("bottom_near"), "from_high": r.get("from_high"),
    "disp": r.get("disp"), "review": r.get("review"), "vr": r.get("vr"),
}
json.dump(out, open(f"results/dbg_{code}.json", "w", encoding="utf-8"), ensure_ascii=False, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "bars"}, ensure_ascii=False, default=str)[:3000])
