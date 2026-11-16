"""위험·바닥 지표 항목별 검증(2026-11-16, 머니파이 요청) — 각 상태가 켜진 날 이후 코스피가 어떻게 됐나.
VIX가 위험 쪽인지 바닥 쪽인지 가리려고 만듦. 결과: results/risk_study.txt, results/risk_study.json
- 자료: 코스피(KS11, 2000~), VIX(^VIX), 미국채 10년(^TNX). 미국 지표는 그 전날 미국 종가를 씀(한국 장 시작 전에 알 수 있는 값).
- 날 단위: 켜진 모든 날의 20·60거래일 뒤 수익률·60일 안 최대 하락. 날이 겹쳐 부풀므로 '사건'(20거래일 넘게 꺼졌다가 다시 켜진 첫날) 기준도 같이.
- 비교 기준: 전체 날 평균. 신용잔고는 5년치만 있어 뺌, 내 종목 역배열은 종목 구성 탓에 뺌."""
import contextlib
import io
import json
import os

import numpy as np
import pandas as pd

os.makedirs("results", exist_ok=True)
START = "2000-01-01"


def kospi():
    try:
        import FinanceDataReader as fdr
        with contextlib.redirect_stdout(io.StringIO()):
            s = fdr.DataReader("KS11", START)["Close"].dropna()
        if len(s) > 3000:
            return s
    except Exception as e:
        print("fdr 실패", e)
    import yfinance as yf
    return yf.Ticker("^KS11").history(start=START, auto_adjust=False)["Close"].dropna().tz_localize(None)


def yf_close(sym):
    import yfinance as yf
    h = yf.Ticker(sym).history(start="1995-01-01", auto_adjust=False)["Close"].dropna()
    h.index = pd.to_datetime(h.index.date)
    return h


def rsi(close, n=14):
    d = close.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + g / l)


def prev_us(us, idx):
    """한국 날짜 d에 대해 d 이전(같은 날 제외) 마지막 미국 값"""
    u = us.copy()
    u.index = u.index + pd.Timedelta(days=1)          # 미국 d-1 종가 → 한국 d 아침에 앎
    return u.reindex(u.index.union(idx)).ffill().reindex(idx)


ks = kospi()
ks.index = pd.to_datetime(ks.index).normalize()
idx = ks.index
vix = prev_us(yf_close("^VIX"), idx)
tnx = prev_us(yf_close("^TNX"), idx)
vix_raw = yf_close("^VIX")
vix10 = prev_us(vix_raw / vix_raw.shift(10) - 1, idx) * 100
tnx_raw = yf_close("^TNX")
y10 = prev_us(tnx_raw - tnx_raw.shift(10), idx)

disp = ks / ks.rolling(50).mean() * 100
r14 = rsi(ks)
hi250 = ks.rolling(250, min_periods=60).max()
fh = (ks / hi250 - 1) * 100
low_pos = ks.rolling(250, min_periods=60).apply(lambda w: len(w) - 1 - int(np.argmin(w)), raw=True)   # 52주 최저가 며칠 전

f20 = (ks.shift(-20) / ks - 1) * 100
f60 = (ks.shift(-60) / ks - 1) * 100
fwd_min = pd.concat([ks.shift(-k) for k in range(1, 61)], axis=1).min(axis=1)
dd60 = (fwd_min / ks - 1) * 100

cross25 = (vix >= 25) & (vix.rolling(20).max().shift(1) < 25)
S = {
    # VIX
    "VIX 13 이하(안일)": vix <= 13,
    "VIX 13~20": (vix > 13) & (vix < 20),
    "VIX 20~25": (vix >= 20) & (vix < 25),
    "VIX 25~30": (vix >= 25) & (vix < 30),
    "VIX 30~40": (vix >= 30) & (vix < 40),
    "VIX 40 이상": vix >= 40,
    "VIX 25 처음 돌파(20일 만에)": cross25,
    "VIX 10일 +30% 급등": vix10 >= 30,
    "위험항목: VIX 25↑ 또는 10일 30%↑": (vix >= 25) | (vix10 >= 30),
    "바닥항목: VIX 30↑": vix >= 30,
    # 그 밖 위험 항목
    "위험: 코스피 이격도(50일) 120↑": disp >= 120,
    "위험: 코스피 RSI 70↑": r14 >= 70,
    "위험: 미국채10년 10일 +0.3%p↑": y10 >= 0.3,
    "이격도 110↑": disp >= 110,
    # 바닥 항목
    "바닥: 이격도 90↓": disp <= 90,
    "바닥: RSI 35↓": r14 <= 35,
    "바닥: 고점 -20%↓·20일 신저점 없음": (fh <= -20) & (low_pos >= 20),
}
RISK4 = (disp >= 120).astype(int) + (r14 >= 70).astype(int) + ((vix >= 25) | (vix10 >= 30)).astype(int) + (y10 >= 0.3).astype(int)
RISK3 = (disp >= 120).astype(int) + (r14 >= 70).astype(int) + (y10 >= 0.3).astype(int)      # VIX 뺀 위험
for k in (1, 2, 3):
    S[f"위험 4항목 중 {k}개 이상"] = RISK4 >= k
    S[f"위험 VIX 빼고 3항목 중 {k}개 이상"] = RISK3 >= k

valid = f60.notna() & vix.notna() & r14.notna() & disp.notna()
base = {"n": int(valid.sum()), "f20": float(f20[valid].mean()), "f60": float(f60[valid].mean()),
        "neg60": float((f60[valid] < 0).mean() * 100), "dd60": float(dd60[valid].mean()),
        "dd10": float((dd60[valid] <= -10).mean() * 100)}


def episodes(mask):
    m = mask.fillna(False).values
    first, off = [], 99
    for i, v in enumerate(m):
        if v and off > 20:
            first.append(i)
        off = 0 if v else off + 1
    return first


def stat(mask):
    m = mask.fillna(False) & valid
    out = {"n": int(m.sum())}
    if out["n"] == 0:
        return out
    out.update({"f20": float(f20[m].mean()), "f60": float(f60[m].mean()), "f60_med": float(f60[m].median()),
                "neg60": float((f60[m] < 0).mean() * 100), "dd60": float(dd60[m].mean()),
                "dd10": float((dd60[m] <= -10).mean() * 100)})
    ep = [i for i in episodes(mask) if valid.iloc[i]]
    out["ep"] = len(ep)
    if ep:
        out.update({"ep_f20": float(f20.iloc[ep].mean()), "ep_f60": float(f60.iloc[ep].mean()),
                    "ep_neg60": float((f60.iloc[ep] < 0).mean() * 100), "ep_dd60": float(dd60.iloc[ep].mean()),
                    "ep_dates": [f"{idx[i]:%Y-%m-%d}" for i in ep][-12:]})
    return out


res = {"made": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "from": f"{idx[valid.values][0]:%Y-%m-%d}",
       "to": f"{idx[valid.values][-1]:%Y-%m-%d}", "base": base, "rows": {k: stat(v) for k, v in S.items()}}
with open("results/risk_study.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

L = [f"위험·바닥 항목 검증 — 코스피 {res['from']} ~ {res['to']} (60거래일 뒤까지 있는 날)",
     "열: 날수 | 20일 뒤 평균% | 60일 뒤 평균%(중앙) | 60일 뒤 손실 확률% | 60일 안 최대하락 평균% | -10% 넘게 빠진 확률% || 사건수 | 사건 첫날 60일 뒤 평균% | 손실확률% | 최대하락%",
     f"{'전체(기준)':<30} {base['n']:>5} | {base['f20']:>5.1f} | {base['f60']:>5.1f}       | {base['neg60']:>4.0f} | {base['dd60']:>6.1f} | {base['dd10']:>4.0f}"]
for k, v in res["rows"].items():
    if not v.get("n"):
        L.append(f"{k:<30} 없음")
        continue
    s = (f"{k:<30} {v['n']:>5} | {v['f20']:>5.1f} | {v['f60']:>5.1f}({v['f60_med']:>5.1f}) | {v['neg60']:>4.0f} | {v['dd60']:>6.1f} | {v['dd10']:>4.0f}")
    if v.get("ep"):
        s += f" || {v['ep']:>3} | {v['ep_f60']:>6.1f} | {v['ep_neg60']:>4.0f} | {v['ep_dd60']:>6.1f}  최근: {', '.join(v['ep_dates'][-4:])}"
    L.append(s)
open("results/risk_study.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
