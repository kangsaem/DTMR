"""200일 이격 위험 항목 기준 낮추기 비교(2026-11-25 사용자: 150↑는 1999·2026뿐 — 현실성?)
켜진 날 전부 기준(2026-11-16 risk_study와 같은 방식): 60일 뒤 평균, 60일 안 -10%↓ 확률, 구간 수, 50일 이격 120↑와 겹침. 기간 1996~ / 2003~(외환위기 뒤) / 2010~"""
import numpy as np, pandas as pd, FinanceDataReader as fdr
ks = fdr.DataReader("KS11", "1990-01-01")["Close"].dropna()
d200 = ks / ks.rolling(200).mean() * 100; d50 = ks / ks.rolling(50).mean() * 100
n = len(ks); c = ks.values
fwd60 = pd.Series([(c[i + 60] / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=ks.index)
dd60 = pd.Series([(c[i + 1:i + 61].min() / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=ks.index)
def runs(on):
    r, cur, idx = [], None, list(on.index)
    for i in range(len(on)):
        if on.iloc[i]:
            if cur and i - cur[1] <= 20: cur[1] = i
            else:
                if cur: r.append(cur)
                cur = [i, i]
    if cur: r.append(cur)
    return [(idx[a], idx[b]) for a, b in r]
def row(nm, on, since):
    on = on.loc[since:].fillna(False); m = on & fwd60.loc[since:].notna()
    if m.sum() == 0: return f"{nm:<22} 0일"
    f, dd = fwd60.loc[since:][m], dd60.loc[since:][m]
    rr = runs(on)
    return (f"{nm:<22} {len(rr):>2}구간 {int(on.sum()):>4}일 | 60일 뒤 {f.mean():+5.1f}% · 하락 {(f < 0).mean() * 100:3.0f}% | 60일 안 -10%↓ {(dd <= -10).mean() * 100:3.0f}%"
            f" · 최대 하락 평균 {dd.mean():+5.1f}% | 50일 이격 120↑와 겹침 {((on & (d50.loc[since:] >= 120)).sum() / max(on.sum(), 1)) * 100:3.0f}%"
            f" | 최근 구간 {', '.join(f'{a:%y.%m}' for a, b in rr[-4:])}")
for since in ("1996-01-01", "2003-01-01", "2010-01-01"):
    base = fwd60.loc[since:].dropna(); bdd = dd60.loc[since:].dropna()
    print(f"\n===== {since[:4]}~ · 기준(아무 날) 60일 뒤 {base.mean():+.1f}% · 하락 {(base < 0).mean() * 100:.0f}% · 60일 안 -10%↓ {(bdd <= -10).mean() * 100:.0f}% · 최대 하락 평균 {bdd.mean():+.1f}%")
    for th in (110, 115, 120, 125, 130, 140, 150):
        print(row(f"200일 이격 {th}↑", d200 >= th, since))
    print(row("참고: 50일 이격 120↑", d50 >= 120, since))
print(f"\n지금 200일 이격 {d200.iloc[-1]:.0f} · 50일 이격 {d50.iloc[-1]:.0f} ({ks.index[-1]:%Y-%m-%d})")
