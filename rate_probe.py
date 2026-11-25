"""금리 위험 항목 다시 보기(2026-11-25 사용자: '급등이 아니라 슬금슬금 오르다 임계점을 넘으면 중력처럼 작용')
미국 10년물 = FRED DGS10(1962~). 코스피 FDR KS11(1998~). 60일·120일 둘 다 봄(천천히 작용하면 120일에서 드러남).
측정: 켜진 날 기준 60일 뒤 평균·60일 안 -10%↓ 확률 / 120일 뒤 평균·120일 안 -15%↓ 확률, 아무 날 대비 배수"""
import numpy as np, pandas as pd, FinanceDataReader as fdr

ks = fdr.DataReader("KS11", "1998-01-01")["Close"].dropna(); I = ks.index; n = len(ks); c = ks.values
def fwd(h): return pd.Series([(c[i + h] / c[i] - 1) * 100 if i + h < n else np.nan for i in range(n)], index=I)
def ddn(h): return pd.Series([(c[i + 1:i + h + 1].min() / c[i] - 1) * 100 if i + h < n else np.nan for i in range(n)], index=I)
f60, d60, f120, d120 = fwd(60), ddn(60), fwd(120), ddn(120)

t = fdr.DataReader("FRED:DGS10", "1990-01-01"); t = pd.to_numeric(t.iloc[:, 0], errors="coerce").dropna()
ma200 = t.rolling(200).mean()
lv5 = t.rolling(1250, min_periods=500).apply(lambda x: (x <= x[-1]).mean() * 100, raw=True)
R = lambda s: s.reindex(I, method="ffill")
y = R(t)
V = {
    "지금: 10일 +0.3%p↑": R(t - t.shift(10)) >= 0.3,
    "20일 +0.5%p↑": R(t - t.shift(20)) >= 0.5,
    "수준 4.0% 이상": y >= 4.0, "수준 4.5% 이상": y >= 4.5, "수준 5.0% 이상": y >= 5.0,
    "1년 +1.0%p↑": R(t - t.shift(250)) >= 1.0, "1년 +1.5%p↑": R(t - t.shift(250)) >= 1.5,
    "6개월 +0.75%p↑": R(t - t.shift(125)) >= 0.75,
    "200일 평균 위 + 평균 상승": R((t > ma200) & (ma200 > ma200.shift(20))),
    "5년 중 상위 10%": R(lv5) >= 90, "5년 중 상위 20%": R(lv5) >= 80,
    "4.5%↑ + 1년 +1%p↑": (y >= 4.5) & (R(t - t.shift(250)) >= 1.0),
    "4.0%↑ + 200일 평균 상승": (y >= 4.0) & R(ma200 > ma200.shift(20)),
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
    s = cond.loc[since:].astype("boolean"); ok = s.notna() & f120.loc[since:].notna(); on = s.fillna(False).astype(bool)
    o = on & ok
    if o.sum() == 0: return f"{nm:<24} 0일"
    b10, b15 = (d60.loc[since:][ok] <= -10).mean() * 100, (d120.loc[since:][ok] <= -15).mean() * 100
    p10, p15 = (d60.loc[since:][o] <= -10).mean() * 100, (d120.loc[since:][o] <= -15).mean() * 100
    rr = runs(on.values); ix = on.index
    return (f"{nm:<24} {len(rr):>3}구간 {int(o.sum()):>4}일({o.sum() / ok.sum() * 100:4.1f}%) | 60일 {f60.loc[since:][o].mean():+5.1f}% · -10%↓ {p10:3.0f}%(×{p10 / b10:.1f})"
            f" | 120일 {f120.loc[since:][o].mean():+5.1f}% · -15%↓ {p15:3.0f}%(×{p15 / b15:.1f}) | 구간 {', '.join(f'{ix[a]:%y.%m}' for a, b in rr[-5:])}")

for since in ("2000-01-01", "2010-01-01"):
    ok = f120.loc[since:].notna()
    print(f"\n===== {since[:4]}~ 아무 날: 60일 {f60.loc[since:][ok].mean():+.1f}% · -10%↓ {(d60.loc[since:][ok] <= -10).mean() * 100:.0f}% | 120일 {f120.loc[since:][ok].mean():+.1f}% · -15%↓ {(d120.loc[since:][ok] <= -15).mean() * 100:.0f}%")
    for k, v in V.items(): print(row(k, v, since))
print(f"\n지금 미국 10년물 {t.iloc[-1]:.2f}% ({t.index[-1]:%Y-%m-%d}) · 1년 변화 {t.iloc[-1] - t.iloc[-251]:+.2f}%p · 200일 평균 {ma200.iloc[-1]:.2f}% · 5년 중 {lv5.iloc[-1]:.0f}%")
print("연도별 평균 금리:", " ".join(f"{yy}:{v:.1f}" for yy, v in t.groupby(t.index.year).mean().loc[2000:].items()))
