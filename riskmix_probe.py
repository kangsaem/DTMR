"""(riskmix) 위험 시장 항목 후보 8개 중 5개 조합 56개 비교(2026-11-25 사용자 C안). 내 종목 역배열은 따로(앱 6번째).
평가 1999~2026, 2개 이상 구간(5거래일 안 끊김은 한 구간) 기준:
 · 큰 고점 7번(2000-01, 2002-04, 2007-10, 2011-05, 2018-01, 2021-07, 2026-06) 중 고점 전 12개월~고점 뒤 1개월 안에 구간이 시작된 수 = 잡은 고점
 · 맞음 = 시작 뒤 2년 안 저점이 시작일 지수보다 아래 / 헛신호 = 아님 (2025-01 이후 시작은 아직 판정 안 함)
 · 2개↑·3개↑ 날의 60일 안 -10% 확률(아무 날 = 26%)"""
import functools, itertools, json, numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m, foreign

ks = fdr.DataReader("KS11", "1997-01-01")["Close"].dropna(); I = ks.index; n = len(ks); c = ks.values
dd60 = pd.Series([c[i + 1:i + 61].min() / c[i] * 100 - 100 if i + 60 < n else np.nan for i in range(n)], index=I)
lo2y = pd.Series([c[i + 1:i + 501].min() / c[i] * 100 - 100 if i + 500 < n else np.nan for i in range(n)], index=I)
d50 = ks / ks.rolling(50).mean() * 100; d200 = ks / ks.rolling(200).mean() * 100; rs = m.rsi(ks)
fh = (ks / ks.rolling(250, min_periods=1).max() - 1) * 100
t10 = fdr.DataReader("FRED:DGS10", "1996-01-01"); t10 = pd.to_numeric(t10.iloc[:, 0], errors="coerce").dropna()
y10c = (t10 - t10.shift(10)).reindex(I, method="ffill"); y20 = (t10 - t10.shift(20)).reindex(I, method="ffill"); ylv = t10.reindex(I, method="ffill")
f = foreign.series()
fa = pd.Series({pd.Timestamp(k): float(v) for k, v in json.load(open("results/foreign_kospi.json")).items()}).sort_index(); fa = fa[fa.index >= "2006-01-01"]
f = pd.concat([fa[fa.index < f.index[0]], f]).sort_index(); f = f[~f.index.duplicated(keep="last")].reindex(I)
f20 = f.rolling(20, min_periods=18).sum().where(f.notna())
m._freesis_rows = functools.partial(m._freesis_rows, years=25)
cred, dep = m.credit_tables(); ratio = (cred["cred"] / dep).reindex(I, method="ffill", limit=5)
p5 = ratio.rolling(1250, min_periods=250).apply(lambda x: (x[~np.isnan(x)] <= x[-1]).mean() * 100 if not np.isnan(x[-1]) else np.nan, raw=True)

P = pd.DataFrame({"RSI70": rs >= 70, "이격120": d50 >= 120, "200일150": d200 >= 150, "금리10일+0.3": y10c >= 0.3,
                  "금리20일+0.5": y20 >= 0.5, "금리5%": ylv >= 5, "신용상위10": p5 >= 90, "외국인": (fh >= -3) & (f20 < 0)}).fillna(False)
P = P[P.index >= "1999-01-01"]
PEAKS = [pd.Timestamp(x) for x in ["2000-01-04", "2002-04-18", "2007-10-31", "2011-04-27", "2018-01-29", "2021-07-06", "2026-06-22"]]
ok60 = dd60.reindex(P.index).notna(); base = (dd60.reindex(P.index)[ok60] <= -10).mean() * 100
print(f"아무 날 60일 안 -10%: {base:.0f}% · 항목별 켜진 날 %: " + ", ".join(f"{k} {P[k].mean()*100:.1f}" for k in P.columns))

def eps(cnt):
    on = cnt.values >= 2; idx = cnt.index; out = []; i = 0
    while i < len(on):
        if on[i]:
            j = k = i; gap = 0
            while k + 1 < len(on) and gap <= 5:
                k += 1
                if on[k]: j = k; gap = 0
                else: gap += 1
            out.append(idx[i]); i = j + 1
        else: i += 1
    return out

rows = []
for combo in itertools.combinations(P.columns, 5):
    cnt = P[list(combo)].sum(axis=1); st = eps(cnt)
    caught = [p for p in PEAKS if any(p - pd.Timedelta(days=365) <= s <= p + pd.Timedelta(days=31) for s in st)]
    judged = [s for s in st if s < pd.Timestamp("2025-01-01") and not np.isnan(lo2y.get(s, np.nan))]
    hit = sum(lo2y[s] < 0 for s in judged); false = len(judged) - hit
    r2 = (dd60.reindex(P.index)[(cnt >= 2) & ok60] <= -10).mean() * 100 if ((cnt >= 2) & ok60).any() else np.nan
    r3 = (dd60.reindex(P.index)[(cnt >= 3) & ok60] <= -10).mean() * 100 if ((cnt >= 3) & ok60).any() else np.nan
    rows.append(dict(c=" + ".join(combo), peaks=len(caught), pk=",".join(f"{p:%y}" for p in caught), n=len(st), hit=hit, false=false,
                     d2=(cnt >= 2).mean() * 100, r2=r2, d3=(cnt >= 3).mean() * 100, r3=r3))
D = pd.DataFrame(rows).sort_values(["peaks", "false", "r2"], ascending=[False, True, False])
def show(r, tag=""):
    print(f"{tag}{r.c}\n     고점 {r.peaks}/7 [{r.pk}] · 구간 {r.n}(맞음 {r.hit}·헛 {r.false}) · 2↑ 날 {r.d2:.1f}% -10% {r.r2:.0f}% · 3↑ 날 {r.d3:.1f}% -10% {r.r3:.0f}%")
print("\n=== 옛·새 ===")
for nm, cb in (("옛 ", "RSI70 + 이격120 + 200일150 + 금리10일+0.3 + 신용상위10"), ("새 ", "이격120 + 200일150 + 금리20일+0.5 + 금리5% + 외국인")):
    show(D[D.c == cb].iloc[0], nm)
print("\n=== 상위 15(잡은 고점 많은 순 → 헛신호 적은 순) ===")
for _, r in D.head(15).iterrows(): show(r)
print("\n=== 헛신호 2개 이하 중 잡은 고점 많은 순 ===")
for _, r in D[D.false <= 2].head(8).iterrows(): show(r)
