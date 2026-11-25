"""시장 위험 지표 6개 전체 점검 + 대체 후보(2026-11-25 사용자). 코스피 2000~ 기준, 켜진 날 전부(날 기준)와 처음 켜진 날(구간 기준) 둘 다.
좋은 위험 항목 = 켜진 날 60일 안 -10% 하락 확률이 아무 날보다 확실히 높고, 60일 뒤 평균이 아무 날보다 낮음. 너무 드물면(구간 2~3번) 쓸모 적음.
자료: 코스피 FDR KS11 · 미국채 10년 FRED DGS10(리포트는 야후 ^TNX, 값 거의 같음) · 달러원 FDR USD/KRW
· 내 종목 역배열 = tickers.json 종목의 과거 주가(지금 목록 기준이라 생존 편향) · 신용잔고/예탁금 = 리포트와 같은 자료(약 5년뿐)"""
import json, numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m

ks = fdr.DataReader("KS11", "1998-01-01")["Close"].dropna()
I = ks.index; n = len(ks); c = ks.values
fwd60 = pd.Series([(c[i + 60] / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
dd60 = pd.Series([(c[i + 1:i + 61].min() / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
rsi = m.rsi(ks); d50 = ks / ks.rolling(50).mean() * 100; d200 = ks / ks.rolling(200).mean() * 100
wk = ks.groupby(pd.Grouper(freq="W-FRI")).last().dropna(); wrsi = m.rsi(wk).reindex(I, method="ffill")

def ext(code, start="1998-01-01"):
    try:
        s = fdr.DataReader(code, start); s = s.iloc[:, 0] if "Close" not in s else s["Close"]
        return pd.to_numeric(s, errors="coerce").dropna()
    except Exception as e:
        print("자료 실패", code, e); return pd.Series(dtype=float)
t10 = ext("FRED:DGS10"); fx = ext("USD/KRW")
y_chg10 = (t10 - t10.shift(10)).reindex(I, method="ffill"); y_chg20 = (t10 - t10.shift(20)).reindex(I, method="ffill")
fx_r = fx.reindex(I, method="ffill"); fx20 = (fx_r / fx_r.shift(20) - 1) * 100

# 내 종목 일봉 역배열 비율(5일선 < 10일선, 리포트 cross_state와 같음)
tk = [t for t in json.load(open("tickers.json", encoding="utf-8")) if t.get("code")]
arr = {}
for t in tk:
    try:
        p = m.load_prices(t["code"])["Close"].dropna()
        p.index = pd.to_datetime(p.index).tz_localize(None) if getattr(p.index, "tz", None) else pd.to_datetime(p.index)
        p = p[~p.index.duplicated()]
        if len(p) > 30: arr[t["code"]] = (p.rolling(5).mean() < p.rolling(10).mean()).astype(float).where(p.rolling(10).mean().notna())
    except Exception as e:
        pass
A = pd.DataFrame(arr).reindex(I).astype(float)
cnt = A.notna().sum(axis=1); bear = (A.sum(axis=1) / cnt).where(cnt >= 10)
print(f"내 종목 {len(arr)}/{len(tk)}개 받음 · 10개 이상 있는 첫날 {bear.dropna().index[0]:%Y-%m-%d}" if bear.notna().any() else "내 종목 자료 없음")

# 신용잔고/예탁금 비율 백분위(그날까지 최대 5년 안, 리포트 credit_hist와 같음)
cpct = pd.Series(np.nan, index=I)
try:
    cred, dep = m.credit_tables(); r = m.credit_series(cred, dep)["ratio"]
    v, ix = r.values, r.index
    pc = pd.Series([float((v[(ix >= ix[i] - pd.DateOffset(years=m.CREDIT_YEARS)) & (ix <= ix[i])] <= v[i]).mean() * 100) if i >= 120 else np.nan for i in range(len(r))], index=ix)
    cpct = pc.reindex(I, method="ffill", limit=5)
    print(f"신용 비율 {ix[0]:%Y-%m-%d} ~ {ix[-1]:%Y-%m-%d} ({len(r)}일) · 백분위는 120일 이후부터")
except Exception as e:
    print("신용 자료 실패", e)

NOW = {
    "R1 RSI 70↑": rsi >= 70, "R2 50일 이격 120↑": d50 >= 120, "R3 200일 이격 150↑": d200 >= 150,
    "R4 금리 10일 +0.3%p↑": y_chg10 >= 0.3, "R5 내 종목 70% 역배열": bear >= 0.7, "R6 신용 상위 10%": cpct >= 90,
}
CAND = {
    "RSI 80↑": rsi >= 80, "주봉 RSI 70↑": wrsi >= 70, "주봉 RSI 80↑": wrsi >= 80,
    "50일 이격 115↑": d50 >= 115, "50일 이격 110↑": d50 >= 110, "200일 이격 140↑": d200 >= 140, "200일 이격 130↑": d200 >= 130,
    "금리 20일 +0.5%p↑": y_chg20 >= 0.5, "금리 10일 +0.2%p↑": y_chg10 >= 0.2,
    "달러원 20일 +3%↑": fx20 >= 3, "달러원 20일 +5%↑": fx20 >= 5,
    "내 종목 50% 역배열": bear >= 0.5, "내 종목 90% 역배열": bear >= 0.9, "신용 상위 20%": cpct >= 80,
}

def runs(on):
    r, cur = [], None
    for i in range(len(on)):
        if on[i]:
            if cur and i - cur[1] <= 20: cur[1] = i
            else:
                if cur: r.append(cur)
                cur = [i, i]
    if cur: r.append(cur)
    return r

def row(nm, cond, since):
    s = cond.loc[since:]; valid = s.notna() & fwd60.loc[since:].notna()
    on = s.fillna(False).astype(bool)
    if valid.sum() == 0: return f"{nm:<22} 자료 없음"
    o = on & valid; base_dd = dd60.loc[since:][valid]
    if o.sum() == 0: return f"{nm:<22} 0일(자료 {valid.sum()}일)"
    f, dd = fwd60.loc[since:][o], dd60.loc[since:][o]
    rr = runs(on.values); ix = on.index
    first = [ix[a] for a, b in rr if pd.notna(fwd60.get(ix[a]))]
    ff = fwd60.reindex(first); fd = dd60.reindex(first)
    p10 = (dd <= -10).mean() * 100; b10 = (base_dd <= -10).mean() * 100
    return (f"{nm:<22} {len(rr):>3}구간 {int(o.sum()):>4}일({o.sum() / valid.sum() * 100:4.1f}%) | 날: 60일 {f.mean():+5.1f}% · -10%↓ {p10:3.0f}%(×{p10 / b10 if b10 else 0:.1f}) · 최대하락 {dd.mean():+5.1f}%"
            f" | 첫날: 60일 {ff.mean():+5.1f}% · -10%↓ {(fd <= -10).mean() * 100:3.0f}% | 최근 {', '.join(f'{ix[a]:%y.%m}' for a, b in rr[-3:])}")

for since in ("2000-01-01", "2010-01-01"):
    b = fwd60.loc[since:].dropna(); bd = dd60.loc[since:].dropna()
    print(f"\n===== {since[:4]}~ 기준(아무 날) 60일 {b.mean():+.1f}% · 하락 {(b < 0).mean() * 100:.0f}% · -10%↓ {(bd <= -10).mean() * 100:.0f}% · 최대하락 {bd.mean():+.1f}%")
    print("-- 지금 항목"); [print(row(k, v, since)) for k, v in NOW.items()]
    print("-- 후보"); [print(row(k, v, since)) for k, v in CAND.items()]

# 게이지 전체: 켜진 항목 수별(자료 없는 항목은 꺼진 것으로 셈 — 리포트와 같음)
sc = sum(v.fillna(False).astype(int) for v in NOW.values())
print("\n===== 지금 위험 게이지 점수별(2010~, 날 기준) — 낮음 0~1 · 주의 2~3 · 경고 4~6")
for lo, hi, nm in ((0, 0, "0개"), (1, 1, "1개"), (2, 3, "2~3개(주의)"), (4, 6, "4개 이상(경고)")):
    msk = (sc >= lo) & (sc <= hi) & fwd60.notna(); msk = msk.loc["2010-01-01":]
    if msk.sum():
        f, dd = fwd60.loc["2010-01-01":][msk], dd60.loc["2010-01-01":][msk]
        print(f"  {nm:<14} {int(msk.sum()):>4}일 | 60일 {f.mean():+5.1f}% · 하락 {(f < 0).mean() * 100:3.0f}% · -10%↓ {(dd <= -10).mean() * 100:3.0f}% · 최대하락 {dd.mean():+5.1f}%")
    else:
        print(f"  {nm:<14} 0일")
print(f"\n지금({I[-1]:%Y-%m-%d}): " + " · ".join(f"{k} {'켜짐' if bool(v.fillna(False).iloc[-1]) else '-'}" for k, v in NOW.items()))
