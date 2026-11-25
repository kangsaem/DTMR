"""코스피 200일 이격 150 이상이 몇 번 있었나(2026-11-25 사용자) — 구간(연속으로 켜진 기간, 20거래일 안에 다시 켜지면 같은 구간)별로"""
import pandas as pd, FinanceDataReader as fdr
ks = fdr.DataReader("KS11", "1980-01-01")["Close"].dropna()
d = ks / ks.rolling(200).mean() * 100
print(f"코스피 {ks.index[0]:%Y-%m-%d} ~ {ks.index[-1]:%Y-%m-%d} · 200일 이격 계산 {d.dropna().index[0]:%Y-%m-%d}~ · 지금 {d.iloc[-1]:.0f}")
for th in (120, 130, 140, 150):
    on = (d >= th).fillna(False); idx = list(ks.index); runs = []; cur = None
    for i, dt in enumerate(idx):
        if on.iloc[i]:
            if cur and i - cur[1] <= 20: cur[1] = i
            else:
                if cur: runs.append(cur)
                cur = [i, i]
    if cur: runs.append(cur)
    print(f"\n■ 200일 이격 {th} 이상: {len(runs)}구간 · 켜진 날 {int(on.sum())}일")
    if th >= 140:
        for a, b in runs:
            seg = d.iloc[a:b + 1]; pk = ks.iloc[a:b + 61].idxmax(); after = ks.iloc[b:b + 127]
            r = lambda n: (ks.iloc[a + n] / ks.iloc[a] - 1) * 100 if a + n < len(ks) else float("nan")
            fut60 = ks.iloc[a + 1:a + 61]
            print(f"  {idx[a]:%Y-%m-%d} ~ {idx[b]:%Y-%m-%d} ({b - a + 1}거래일) · 최고 이격 {seg.max():.0f}({seg.idxmax():%y.%m.%d}) · 첫날 코스피 {ks.iloc[a]:,.0f}"
                  f" · 60일 뒤 {r(60):+.0f}% · 60일 안 최대 하락 {(fut60.min() / ks.iloc[a] - 1) * 100:+.0f}% · 첫날 뒤 최고점 {pk:%y.%m.%d}({(ks[pk] / ks.iloc[a] - 1) * 100:+.0f}%)"
                  f" · 구간 끝 뒤 6개월 안 최저 {(after.min() / ks.iloc[b] - 1) * 100:+.0f}%")
