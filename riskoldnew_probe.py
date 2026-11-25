"""(riskoldnew) 오늘 바꾸기 전 위험 6개(옛) vs 새 6개, 1999~ 같은 측정(2026-11-25 사용자). 둘 다 내 종목 뺀 시장 5개.
옛 = RSI 70↑, 50일 이격 120↑, 200일 이격 150↑, 미국채10년 10일 +0.3%p↑, 신용/예탁금 5년 중 상위 10%(자료 2001-12~, 백분위는 1년 쌓인 뒤)
새 = 50일 이격 120↑, 200일 이격 150↑, 금리 20일 +0.5%p↑, 금리 5%↑, 고점 -3% 안 + 외국인 20일 순매도(2006~)"""
import functools, json, numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m, foreign

ks = fdr.DataReader("KS11", "1997-01-01")["Close"].dropna(); I = ks.index; n = len(ks); c = ks.values
def fw(k, f): return pd.Series([f(c[i + 1:i + k + 1]) / c[i] * 100 - 100 if i + k < n else np.nan for i in range(n)], index=I)
dd60, dd120, up120 = fw(60, np.min), fw(120, np.min), fw(120, np.max)
d50 = ks / ks.rolling(50).mean() * 100; d200 = ks / ks.rolling(200).mean() * 100; rs = m.rsi(ks)
fh = (ks / ks.rolling(250, min_periods=1).max() - 1) * 100
t10 = fdr.DataReader("FRED:DGS10", "1996-01-01"); t10 = pd.to_numeric(t10.iloc[:, 0], errors="coerce").dropna()
y10c = (t10 - t10.shift(10)).reindex(I, method="ffill"); y20 = (t10 - t10.shift(20)).reindex(I, method="ffill"); ylv = t10.reindex(I, method="ffill")
f = foreign.series()
fa = pd.Series({pd.Timestamp(k): float(v) for k, v in json.load(open("results/foreign_kospi.json")).items()}).sort_index(); fa = fa[fa.index >= "2006-01-01"]
f = pd.concat([fa[fa.index < f.index[0]], f]).sort_index(); f = f[~f.index.duplicated(keep="last")].reindex(I)
f20 = f.rolling(20, min_periods=18).sum().where(f.notna())
m._freesis_rows = functools.partial(m._freesis_rows, years=25)
cred, dep = m.credit_tables()
ratio = (cred["cred"] / dep).reindex(I, method="ffill", limit=5)
p5 = ratio.rolling(1250, min_periods=250).apply(lambda x: (x[~np.isnan(x)] <= x[-1]).mean() * 100 if not np.isnan(x[-1]) else np.nan, raw=True)
print(f"신용/예탁금 백분위 첫날 {p5.dropna().index[0]:%Y-%m-%d}")

OLD = pd.DataFrame({"RSI70": rs >= 70, "이격120": d50 >= 120, "200일150": d200 >= 150, "금리10일+0.3": y10c >= 0.3, "신용상위10": p5 >= 90}).fillna(False)
NEW = pd.DataFrame({"이격120": d50 >= 120, "200일150": d200 >= 150, "금리20일+0.5": y20 >= 0.5, "금리5%": ylv >= 5, "외국인": (fh >= -3) & (f20 < 0)}).fillna(False)

def episodes(cnt, k=2):
    on = cnt >= k; idx = list(cnt.index); eps = []; i = 0
    while i < len(idx):
        if on.iloc[i]:
            j = k2 = i; gap = 0
            while k2 + 1 < len(idx) and gap <= 5:
                k2 += 1
                if on.iloc[k2]: j = k2; gap = 0
                else: gap += 1
            eps.append((idx[i], idx[j], int(cnt.iloc[i:j + 1].max()))); i = j + 1
        else: i += 1
    return eps

for name, D in (("옛 기준", OLD), ("새 기준", NEW)):
    D = D[D.index >= "1999-01-01"]; cnt = D.sum(axis=1)
    print(f"\n===== {name} · 항목별 켜진 날 %: " + ", ".join(f"{k} {D[k].mean()*100:.1f}" for k in D.columns))
    for a, b in [("1999", "2009"), ("2010", "2020"), ("2021", "2026")]:
        sel = (cnt.index.year >= int(a)) & (cnt.index.year <= int(b)); cc = cnt[sel]; ok = dd60.reindex(cc.index).notna()
        s = f"  [{a}~{b}] 아무 날 -10% {(dd60.reindex(cc.index)[ok] <= -10).mean()*100:.0f}%"
        for k in (1, 2, 3, 4):
            mm = (cc >= k) & ok
            s += f" | {k}↑ 날 {(cc>=k).mean()*100:.1f}% -10% " + (f"{(dd60.reindex(cc.index)[mm] <= -10).mean()*100:.0f}%" if mm.any() else "-")
        print(s)
    eps = episodes(cnt)
    print(f"  2개 이상 구간 {len(eps)}개 (켜진 날 → 1년 안 고점 → 그 뒤 2년 안 저점, 켜진 날 대비)")
    for d0, d1, mx in eps:
        s = ks[d0:]; p0 = s.iloc[0]; w = s.iloc[:500]; pk_d = w.iloc[:250].idxmax(); pk = w[pk_d]; lo = w[pk_d:].min()
        items = [k for k in D.columns if D.loc[d0:d1, k].any()]
        print(f"   {d0:%Y-%m-%d}~{d1:%Y-%m-%d} 최대 {mx}개 [{', '.join(items)}] · 60일 안 최저 {dd60[d0]:+.0f}% · 고점 {pk_d:%Y-%m} {pk/p0*100-100:+.0f}% · 그 뒤 저점 {lo/p0*100-100:+.0f}%")
