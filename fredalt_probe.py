"""리포트 VIX·미국채 야후 → FRED 대안 시험(2026-11-25): 정상 경로 + 야후를 일부러 막은 경로"""
import market_report as m, yfinance as yf
for sym in ("^VIX", "^TNX", "^TYX"):
    h = m._yf_close(sym); print("정상", sym, len(h), f"{h.index[-1]}", round(float(h.iloc[-1]), 3), "10일 변화", round(float(h.iloc[-1] - h.iloc[-11]), 3))
def boom(*a, **k): raise RuntimeError("야후 막음(시험)")
yf.Ticker = boom
for sym in ("^VIX", "^TNX", "^TYX"):
    try:
        h = m._yf_close(sym); print("대안", sym, len(h), f"{h.index[-1]}", round(float(h.iloc[-1]), 3), "10일 변화", round(float(h.iloc[-1] - h.iloc[-11]), 3) if len(h) > 11 else None)
    except Exception as e:
        print("대안 실패", sym, type(e).__name__, e)
