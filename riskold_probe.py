"""(riskold) 위험 지표(새 6개, 시장 5개 — 내 종목 뺌)가 2000~2020년에도 작동했나(2026-11-25 사용자).
2개 이상 켜진 구간(5거래일 안 끊김은 한 구간)마다: 기간, 최대 개수, 켜진 항목, 시작일 뒤 60·120일 안 최대 하락, 시작일 기준 이후 최고점까지 더 오른 폭.
외국인 자료 2006~ (그 전은 꺼짐). 기간별 2·3개 이상 결과도."""
import json, numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m, foreign

ks = fdr.DataReader("KS11", "1997-01-01")["Close"].dropna()
I = ks.index; n = len(ks); c = ks.values
def fw(k, f):
    return pd.Series([f(c[i + 1:i + k + 1]) / c[i] * 100 - 100 if i + k < n else np.nan for i in range(n)], index=I)
dd60, dd120, up120 = fw(60, np.min), fw(120, np.min), fw(120, np.max)
d50 = ks / ks.rolling(50).mean() * 100; d200 = ks / ks.rolling(200).mean() * 100
fh = (ks / ks.rolling(250, min_periods=1).max() - 1) * 100
t10 = fdr.DataReader("FRED:DGS10", "1996-01-01"); t10 = pd.to_numeric(t10.iloc[:, 0], errors="coerce").dropna()
y20 = (t10 - t10.shift(20)).reindex(I, method="ffill"); ylv = t10.reindex(I, method="ffill")
f = foreign.series()
fa = pd.Series({pd.Timestamp(k): float(v) for k, v in json.load(open("results/foreign_kospi.json")).items()}).sort_index()
fa = fa[fa.index >= "2006-01-01"]
f = pd.concat([fa[fa.index < f.index[0]], f]).sort_index(); f = f[~f.index.duplicated(keep="last")].reindex(I)
f20 = f.rolling(20, min_periods=18).sum().where(f.notna())
R = pd.DataFrame({"이격120": d50 >= 120, "200일150": d200 >= 150, "금리20일+0.5": y20 >= 0.5, "금리5%": ylv >= 5,
                  "외국인": (fh >= -3) & (f20 < 0)}).fillna(False)
R = R[R.index >= "1999-01-01"]; cnt = R.sum(axis=1)

print("항목별 켜진 날 % (1999~):", ", ".join(f"{k} {R[k].mean()*100:.1f}" for k in R.columns))
for a, b in [("1999", "2009"), ("2010", "2020"), ("2021", "2026")]:
    sel = (cnt.index.year >= int(a)) & (cnt.index.year <= int(b)); cc = cnt[sel]; ok = dd60.reindex(cc.index).notna()
    base = (dd60.reindex(cc.index)[ok] <= -10).mean() * 100
    s = f"[{a}~{b}] 아무 날 60일 안 -10% {base:.0f}%"
    for k in (1, 2, 3):
        mm = (cc >= k) & ok
        s += f" | {k}개↑ 날 {(cc>=k).mean()*100:.1f}% · -10% {(dd60.reindex(cc.index)[mm] <= -10).mean()*100 if mm.any() else float('nan'):.0f}%"
    print(s)

on = cnt >= 2; eps = []; i = 0; idx = list(cnt.index)
while i < len(idx):
    if on.iloc[i]:
        j = i; gap = 0; k = i
        while k + 1 < len(idx) and gap <= 5:
            k += 1
            if on.iloc[k]: j = k; gap = 0
            else: gap += 1
        eps.append((i, j)); i = j + 1
    else:
        i += 1
print(f"\n2개 이상 구간 {len(eps)}개")
for a, b in eps:
    d0, d1 = idx[a], idx[b]; seg = R.iloc[a:b + 1]; mx = int(cnt.iloc[a:b + 1].max())
    items = [k for k in R.columns if seg[k].any()]
    p0 = ks[d0]; after = ks[d0:]; pk_i = after.iloc[:250].idxmax(); pk = after.iloc[:250].max()
    print(f"  {d0:%Y-%m-%d} ~ {d1:%Y-%m-%d} ({b-a+1}일) 최대 {mx}개 [{', '.join(items)}]"
          f" · 60일 안 최저 {dd60[d0]:+.0f}% · 120일 안 최저 {dd120[d0]:+.0f}% · 120일 안 최고 {up120[d0]:+.0f}%"
          f" · 1년 안 고점 {pk_i:%Y-%m-%d}(시작 대비 {pk/p0*100-100:+.0f}%)")
