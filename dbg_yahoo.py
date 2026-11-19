"""야후 chart API 원본 응답 저장(머니파이 지수 카드 점검용, 2026-11-19). python dbg_yahoo.py ^IXIC 1d 2m → results/dbg_yahoo_<sym>.json"""
import json, sys, time, urllib.parse, urllib.request
sym, rng, itv = (sys.argv[1:] + ["^IXIC", "1d", "2m"][len(sys.argv) - 1:])[:3]
u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range={rng}&interval={itv}&_={int(time.time())}"
req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
j = json.load(urllib.request.urlopen(req, timeout=20))
r = j["chart"]["result"][0]
m = r["meta"]; ts = r.get("timestamp") or []; cl = r["indicators"]["quote"][0].get("close") or []
fmt = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t)) + "Z" if t else None
out = {"url": u, "fetched": fmt(time.time()), "currentTradingPeriod": m.get("currentTradingPeriod"), "regularMarketTime": fmt(m.get("regularMarketTime")),
       "regularMarketPrice": m.get("regularMarketPrice"), "n": len(ts), "first": fmt(ts[0]) if ts else None, "last": fmt(ts[-1]) if ts else None,
       "nulls": sum(1 for v in cl if v is None), "gaps_over_10m": [[fmt(a), fmt(b)] for a, b in zip(ts, ts[1:]) if b - a > 600][:20],
       "tail": [[fmt(t), v] for t, v in list(zip(ts, cl))[-5:]]}
safe = sym.replace("^", "").replace("=", "_")
json.dump(out, open(f"results/dbg_yahoo_{safe}.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
