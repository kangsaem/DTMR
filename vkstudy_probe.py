"""VKOSPI 바닥 항목(30 이하 + 60거래일 안 30 초과) 켜진 구간의 코스피 위치(2026-11-23)
구간 = 켜짐이 10거래일 넘게 끊기면 새 구간. 각 구간 첫날: 코스피 종가, 직전 120거래일 최저 대비, 그 뒤 20·60·120거래일 수익률, 첫날이 저점 뒤 며칠인지"""
import pandas as pd, FinanceDataReader as fdr
import market_report as m, vkospi
s = vkospi.series(); on = m.vkospi_on(s)
ks = fdr.DataReader("KS11", "2009-06-01")["Close"].dropna()
days = [d for d, v in on.items() if v]
eps, cur = [], None
for d in days:
    if cur and len(s[cur[1]:d]) - 1 <= 10: cur[1] = d
    else:
        cur = [d, d]; eps.append(cur)
allr = {n: ks.pct_change(n).shift(-n).dropna() * 100 for n in (20, 60, 120)}
print("전체 평균(2010~) 20/60/120일 뒤:", " / ".join(f"{allr[n]['2010':].mean():+.1f}%" for n in (20, 60, 120)))
print(f"{'켜진 구간':<25}{'일수':>4} {'VK최고':>6} {'코스피':>8} {'저점대비':>7} {'저점뒤':>5} {'20일':>7} {'60일':>7} {'120일':>7}")
for a, b in eps:
    i = ks.index.searchsorted(a); px = ks.iloc[i]
    w = ks.iloc[max(0, i - 120):i + 1]; lo_d = w.idxmin()
    r = {n: (ks.iloc[i + n] / px - 1) * 100 if i + n < len(ks) else None for n in (20, 60, 120)}
    print(f"{a:%Y-%m-%d} ~ {b:%Y-%m-%d}  {int(on[a:b].sum()):>4} {s[:a].tail(60).max():>6.1f} {px:>8.0f} {(px / w.min() - 1) * 100:>+6.1f}% {len(ks[lo_d:a]) - 1:>5} "
          + " ".join(f"{r[n]:>+6.1f}%" if r[n] is not None else f"{'-':>7}" for n in (20, 60, 120)))
